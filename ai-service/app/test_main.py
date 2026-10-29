from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_returns_status():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'UP'

def test_corpus_status_does_not_claim_fake_data():
    response = client.get('/corpus/status')
    assert response.status_code == 200
    data = response.json()
    assert 'records' in data
    assert 'do not establish' in data['note']
    assert data['records'] >= 0
    assert 'duplicate_check' in data

def test_research_rejects_short_query():
    response = client.get('/research?q=ab')
    assert response.status_code == 422


def test_case_cut_marks_missing_source_honestly():
    response = client.post('/case-cut', json={'query': 'registered sale deed title possession dispute'})
    assert response.status_code == 200
    body = response.json()
    assert len(body['sections']) == 11
    assert 'disclaimer' in body


def test_search_results_do_not_repeat_same_title():
    response = client.get('/research', params={'q': 'registered sale deed title possession', 'limit': 10})
    assert response.status_code == 200
    results = response.json()['results']
    titles = [r['cause_title'] for r in results]
    assert len(titles) == len(set(titles))


def test_research_keeps_distinct_records_without_titles():
    from app import main as service
    original = (service.records, service.vectorizer, service.matrix)
    try:
        service.records = [
            {"case_id": "CASE-A", "document_text": "patta ownership dispute in a village", "source_url": None, "_normalised_text": "patta ownership dispute in a village", "full_text": "patta ownership dispute in a village", "_is_demo": False},
            {"case_id": "CASE-B", "document_text": "patta ownership dispute and survey records", "source_url": None, "_normalised_text": "patta ownership dispute and survey records", "full_text": "patta ownership dispute and survey records", "_is_demo": False},
        ]
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity as _unused
        service.vectorizer = TfidfVectorizer().fit([r["full_text"] for r in service.records])
        service.matrix = service.vectorizer.transform([r["full_text"] for r in service.records])
        found = service.search("patta ownership dispute", 10, dataset="existing")
        assert len(found) == 2
        assert {r["case_id"] for r in found} == {"CASE-A", "CASE-B"}
    finally:
        service.records, service.vectorizer, service.matrix = original


def test_analyse_keeps_results_without_source_urls(monkeypatch):
    from app import main as service
    monkeypatch.setattr(service, "search", lambda *a, **k: [{"case_id":"CASE-X", "cause_title":"Case title unavailable", "source_url":None, "relevant_statutes":[], "source_excerpt":"Relevant retrieved text"}])
    response = client.post('/analyse', json={'query':'patta ownership dispute', 'dataset':'madras'})
    assert response.status_code == 200
    body = response.json()
    assert body['count'] == 1
    assert body['retrieved_cases'][0]['case_id'] == 'CASE-X'


def test_case_cut_uses_retrieved_record_without_source_url(monkeypatch):
    from app import main as service
    monkeypatch.setattr(service, "search", lambda *a, **k: [{"case_id":"CASE-X", "cause_title":"Case title unavailable", "source_url":None, "source_excerpt":"Retrieved passage", "relevance_terms":["patta"]}])
    response = client.post('/case-cut', json={'query':'patta ownership dispute', 'dataset':'madras'})
    assert response.status_code == 200
    body = response.json()
    assert body['retrieved_record_count'] == 1
    assert body['authorities'][0]['case_id'] == 'CASE-X'


def test_madras_search_returns_records_with_vaquill_field_names(monkeypatch):
    from app import main as service
    from sklearn.feature_extraction.text import HashingVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    sample = [
        {"case_id": "HCMA0001", "title": "Patta title dispute", "court": "Madras High Court",
         "decision_date": "2015-03-19", "case_number": "WP 123 of 2014",
         "text": "Patta and agricultural land ownership dispute involving sale deed and possession."},
        {"case_id": "HCMA0002", "title": "Land acquisition matter", "court": "Madras High Court",
         "decision_date": "2018-01-12", "text": "Land acquisition and compensation dispute."},
    ]
    old = (service.candidate_records, service.candidate_vectorizer, service.candidate_matrix)
    try:
        service.candidate_records = [{**r, "full_text": service._record_text(r), "_is_demo": False} for r in sample]
        service.candidate_vectorizer = HashingVectorizer(stop_words="english", ngram_range=(1, 2), n_features=2**12, alternate_sign=False, norm="l2")
        service.candidate_matrix = service.candidate_vectorizer.transform([r["full_text"][:12000] for r in service.candidate_records])
        results = service.search("registered sale deed agricultural land ownership", 5, dataset="madras")
        assert results
        assert results[0]["case_id"] == "HCMA0001"
        assert results[0]["cause_title"] == "Patta title dispute"
        assert results[0]["court"] == "Madras High Court"
        assert results[0]["source_url"] is None
    finally:
        service.candidate_records, service.candidate_vectorizer, service.candidate_matrix = old


def test_madras_search_does_not_return_empty_for_low_overlap_loaded_collection():
    from app import main as service
    from sklearn.feature_extraction.text import HashingVectorizer
    old = (service.candidate_records, service.candidate_vectorizer, service.candidate_matrix)
    try:
        service.candidate_records = [{"case_id": "HCMA0003", "title": "Judgment record", "text": "The court considered revenue records and patta entries.", "full_text": "The court considered revenue records and patta entries.", "_is_demo": False}]
        service.candidate_vectorizer = HashingVectorizer(n_features=2**12, alternate_sign=False, norm="l2")
        service.candidate_matrix = service.candidate_vectorizer.transform([service.candidate_records[0]["full_text"]])
        results = service.search("very unusual unrelated wording", 5, dataset="madras")
        assert len(results) == 1
        assert results[0]["case_id"] == "HCMA0003"
    finally:
        service.candidate_records, service.candidate_vectorizer, service.candidate_matrix = old
