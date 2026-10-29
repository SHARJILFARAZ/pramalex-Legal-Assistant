package in.pramalex.api;
import jakarta.persistence.*;
import java.time.Instant;
@Entity @Table(name="users") class AppUser {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
 @Column(unique=true,nullable=false) public String email;
 @Column(nullable=false) public String passwordHash;
 @Column(nullable=false) public String fullName;
 @Column(nullable=false) public String role="PUBLIC";
 @Column(nullable=false) public String status="ACTIVE";
 public String barCouncilId;
 public Instant createdAt=Instant.now();
}
@Entity @Table(name="legal_cases") class LegalCase {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
 @Column(nullable=false) public Long ownerId;
 @Column(nullable=false) public String title;
 @Column(length=12000,nullable=false) public String facts;
 public String category="PROPERTY";
 public String stage;
 public String relief;
 public String district;
 public String taluk;
 public String village;
 public String surveyNumber;
 public String propertyType;
 public String status="OPEN";
 public Instant createdAt=Instant.now();
 public Instant updatedAt=Instant.now();
}
@Entity @Table(name="legal_documents") class LegalDocument {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
 public Long caseId; public Long ownerId; public String originalName; public String storedName; public String contentType; public Long sizeBytes; public Instant uploadedAt=Instant.now();
}
@Entity @Table(name="case_cuts") class CaseCut {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
 public Long caseId; public Long ownerId; @Column(columnDefinition="LONGTEXT") public String reportJson;
 public Instant createdAt=Instant.now();
}
@Entity @Table(name="audit_events") class AuditEvent {
 @Id @GeneratedValue(strategy=GenerationType.IDENTITY) public Long id;
 public Long actorId; public String action; public String resourceType; public Long resourceId; public Instant createdAt=Instant.now();
}
