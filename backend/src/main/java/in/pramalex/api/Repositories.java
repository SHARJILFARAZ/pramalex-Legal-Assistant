package in.pramalex.api;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.*;
interface UserRepo extends JpaRepository<AppUser,Long>{ Optional<AppUser> findByEmail(String email); long countByRole(String role); long countByStatus(String status); }
interface CaseRepo extends JpaRepository<LegalCase,Long>{ List<LegalCase> findByOwnerIdOrderByUpdatedAtDesc(Long ownerId); Optional<LegalCase> findByIdAndOwnerId(Long id,Long ownerId); long countByOwnerId(Long ownerId); }
interface DocumentRepo extends JpaRepository<LegalDocument,Long>{ List<LegalDocument> findByCaseIdAndOwnerId(Long caseId,Long ownerId); }
interface CaseCutRepo extends JpaRepository<CaseCut,Long>{ List<CaseCut> findByOwnerIdOrderByCreatedAtDesc(Long ownerId); }
interface AuditRepo extends JpaRepository<AuditEvent,Long>{ List<AuditEvent> findTop100ByActorIdOrderByCreatedAtDesc(Long actorId); List<AuditEvent> findTop200ByOrderByCreatedAtDesc(); }
