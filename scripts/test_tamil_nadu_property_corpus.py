import unittest
from build_tamil_nadu_property_corpus import choose_files, get_case_id, get_text, score_row

class CorpusBuilderTests(unittest.TestCase):
    def test_selects_only_madras_and_optional_supreme_parquet(self):
        files = ["data/in_madras_judgments.parquet", "data/in_kerala_judgments.parquet", "data/in_supreme_court_judgments.parquet", "data/in_madras_legislation.parquet"]
        self.assertEqual(choose_files(files, False), ["data/in_madras_judgments.parquet"])
        self.assertEqual(choose_files(files, True), ["data/in_madras_judgments.parquet", "data/in_supreme_court_judgments.parquet"])

    def test_chunk_schema_fields(self):
        row = {"case_id":"MH_123", "chunk_index":2, "text_original":"The suit for partition of ancestral property", "title":"Partition suit"}
        self.assertEqual(get_case_id(row), "MH_123")
        self.assertIn("partition", get_text(row).lower())
        score, hits = score_row(row)
        self.assertGreater(score, 0)
        self.assertIn("partition", " ".join(hits))

    def test_non_property_chunk_does_not_match(self):
        row = {"case_id":"x", "text":"A criminal appeal regarding bail and custody", "title":"State v accused"}
        self.assertEqual(score_row(row)[0], 0)

if __name__ == "__main__": unittest.main()
