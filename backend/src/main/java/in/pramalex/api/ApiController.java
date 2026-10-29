package in.pramalex.api;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.client.RestTemplate;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;

@RestController
@RequestMapping("/api")
class ApiController {
 private final UserRepo users; private final CaseRepo cases; private final DocumentRepo docs; private final CaseCutRepo cuts; private final AuditRepo audits;
 private final PasswordEncoder passwords; private final TokenService tokens; private final RestTemplate http=new RestTemplate();
 @Value("${pramalex.ai.url}") String aiUrl;
 @Value("${pramalex.upload-dir}") String uploadDir;
 ApiController(UserRepo u,CaseRepo c,DocumentRepo d,CaseCutRepo cc,AuditRepo a,PasswordEncoder p,TokenService t){users=u;cases=c;docs=d;cuts=cc;audits=a;passwords=p;tokens=t;}
 AppUser me(Authentication a){return users.findById(Long.valueOf(a.getName())).orElseThrow();}
 void audit(AppUser u,String action,String type,Long id){AuditEvent e=new AuditEvent();e.actorId=u.id;e.action=action;e.resourceType=type;e.resourceId=id;audits.save(e);}
 Map<String,Object> userView(AppUser u){return Map.of("id",u.id,"email",u.email,"fullName",u.fullName,"role",u.role,"status",u.status,"createdAt",u.createdAt);}
 @GetMapping("/health") Map<String,Object> health(){return Map.of("status","UP","service","pramalex-api","database","configured");}
 @PostMapping("/auth/register") ResponseEntity<?> register(@RequestBody Map<String,String> b){
  String email=val(b,"email").toLowerCase(Locale.ROOT), name=val(b,"fullName"), pass=val(b,"password");
  if(email.isBlank()||name.isBlank()||pass.length()<8)return ResponseEntity.badRequest().body(Map.of("error","Name, email and password (8+ characters) are required."));
  if(users.findByEmail(email).isPresent())return ResponseEntity.status(409).body(Map.of("error","Email already registered."));
  AppUser u=new AppUser();u.email=email;u.fullName=name;u.passwordHash=passwords.encode(pass);u.role="PUBLIC";u.status="ACTIVE";users.save(u);
  return ResponseEntity.ok(authPayload(u));
 }
 @PostMapping("/auth/login") ResponseEntity<?> login(@RequestBody Map<String,String>b){
  AppUser u=users.findByEmail(val(b,"email").toLowerCase(Locale.ROOT)).orElse(null);
  if(u==null||!passwords.matches(val(b,"password"),u.passwordHash))return ResponseEntity.status(401).body(Map.of("error","Invalid email or password."));
  if(!"ACTIVE".equals(u.status))return ResponseEntity.status(403).body(Map.of("error","Account is pending verification or disabled."));
  return ResponseEntity.ok(authPayload(u));
 }
 Map<String,Object> authPayload(AppUser u){return Map.of("token",tokens.issue(u),"user",userView(u));}
 @GetMapping("/auth/me") Map<String,Object> current(Authentication a){return userView(me(a));}

 @GetMapping("/dashboard") Map<String,Object> dashboard(Authentication a){
  AppUser u=me(a);var own=cases.findByOwnerIdOrderByUpdatedAtDesc(u.id);
  return Map.of("role",u.role,"totalCases",own.size(),"cases",own.stream().limit(5).map(this::caseView).toList(),
   "caseCuts",cuts.findByOwnerIdOrderByCreatedAtDesc(u.id).size(),"recentActivity",audits.findTop100ByActorIdOrderByCreatedAtDesc(u.id).stream().limit(8).map(e->Map.of("action",e.action,"type",e.resourceType,"at",e.createdAt)).toList());
 }
 @GetMapping("/cases") List<Map<String,Object>> listCases(Authentication a){AppUser u=me(a);if(!canCasework(u))throw new org.springframework.web.server.ResponseStatusException(HttpStatus.FORBIDDEN);return cases.findByOwnerIdOrderByUpdatedAtDesc(u.id).stream().map(this::caseView).toList();}
 @PostMapping("/cases") ResponseEntity<?> createCase(@RequestBody Map<String,Object>b,Authentication a){
  AppUser u=me(a);if(!canCasework(u))return ResponseEntity.status(403).body(Map.of("error","Lawyer or admin role required."));
  String title=String.valueOf(b.getOrDefault("title","")).trim(), facts=String.valueOf(b.getOrDefault("facts","")).trim();
  if(title.isBlank()||facts.length()<20)return ResponseEntity.badRequest().body(Map.of("error","Case title and at least 20 characters of facts are required."));
  LegalCase c=new LegalCase();c.ownerId=u.id;c.title=title;c.facts=facts;c.category=String.valueOf(b.getOrDefault("category","PROPERTY"));c.stage=nullable(b.get("stage"));c.relief=nullable(b.get("relief"));c.district=nullable(b.get("district"));c.taluk=nullable(b.get("taluk"));c.village=nullable(b.get("village"));c.surveyNumber=nullable(b.get("surveyNumber"));c.propertyType=nullable(b.get("propertyType"));cases.save(c);audit(u,"CASE_CREATED","CASE",c.id);
  return ResponseEntity.ok(caseView(c));
 }
 @GetMapping("/cases/{id}") ResponseEntity<?> getCase(@PathVariable Long id,Authentication a){AppUser u=me(a);return cases.findByIdAndOwnerId(id,u.id).<ResponseEntity<?>>map(c->ResponseEntity.ok(caseView(c))).orElseGet(()->ResponseEntity.notFound().build());}
 @PutMapping("/cases/{id}") ResponseEntity<?> updateCase(@PathVariable Long id,@RequestBody Map<String,Object>b,Authentication a){
  AppUser u=me(a);if(!canCasework(u))return ResponseEntity.status(403).build();LegalCase c=cases.findByIdAndOwnerId(id,u.id).orElse(null);if(c==null)return ResponseEntity.notFound().build();
  if(b.containsKey("title"))c.title=String.valueOf(b.get("title"));if(b.containsKey("facts"))c.facts=String.valueOf(b.get("facts"));if(b.containsKey("stage"))c.stage=nullable(b.get("stage"));if(b.containsKey("status"))c.status=String.valueOf(b.get("status"));c.updatedAt=Instant.now();cases.save(c);audit(u,"CASE_UPDATED","CASE",id);return ResponseEntity.ok(caseView(c));
 }
 @PostMapping(value="/cases/{id}/documents",consumes=MediaType.MULTIPART_FORM_DATA_VALUE) ResponseEntity<?> upload(@PathVariable Long id,@RequestPart("file") MultipartFile f,Authentication a)throws Exception{
  AppUser u=me(a);if(!canCasework(u))return ResponseEntity.status(403).build();if(cases.findByIdAndOwnerId(id,u.id).isEmpty())return ResponseEntity.notFound().build();
  if(f.isEmpty()||f.getSize()>20_000_000)return ResponseEntity.badRequest().body(Map.of("error","File is empty or exceeds 20 MB."));
  String ext=Optional.ofNullable(f.getOriginalFilename()).orElse("document").replaceAll("[^a-zA-Z0-9._-]","_");String stored=UUID.randomUUID()+"_"+ext;
  Path dir=Paths.get(uploadDir).toAbsolutePath().normalize();Files.createDirectories(dir);f.transferTo(dir.resolve(stored));
  LegalDocument d=new LegalDocument();d.caseId=id;d.ownerId=u.id;d.originalName=ext;d.storedName=stored;d.contentType=f.getContentType();d.sizeBytes=f.getSize();docs.save(d);audit(u,"DOCUMENT_UPLOADED","DOCUMENT",d.id);return ResponseEntity.ok(Map.of("id",d.id,"name",d.originalName,"sizeBytes",d.sizeBytes));
 }
 @GetMapping("/cases/{id}/documents") List<Map<String,Object>> documents(@PathVariable Long id,Authentication a){AppUser u=me(a);if(cases.findByIdAndOwnerId(id,u.id).isEmpty())throw new org.springframework.web.server.ResponseStatusException(HttpStatus.NOT_FOUND);return docs.findByCaseIdAndOwnerId(id,u.id).stream().map(d->Map.<String,Object>of("id",d.id,"name",d.originalName,"contentType",Objects.toString(d.contentType,""),"sizeBytes",d.sizeBytes,"uploadedAt",d.uploadedAt)).toList();}
 @PostMapping("/cases/{id}/analyse") ResponseEntity<?> analyse(@PathVariable Long id, @RequestParam(defaultValue="existing") String dataset, Authentication a){
  AppUser u=me(a);if(!canCasework(u))return ResponseEntity.status(403).build();LegalCase c=cases.findByIdAndOwnerId(id,u.id).orElse(null);if(c==null)return ResponseEntity.notFound().build();
  try{
   Map<String,Object> req=new LinkedHashMap<>();req.put("query",c.title+"\n"+c.facts);req.put("case_id",c.id);req.put("category",c.category);req.put("court","Madras High Court");req.put("district",c.district);req.put("dataset",dataset.equals("madras")?"madras":"existing");
   Map result=http.postForObject(aiUrl+"/analyse",req,Map.class);audit(u,"CASE_ANALYSED","CASE",id);return ResponseEntity.ok(result==null?Map.of("error","AI service returned no result"):result);
  }catch(Exception ex){return ResponseEntity.status(503).body(Map.of("error","Research service unavailable. Start the FastAPI service and load judgment data.","detail",Objects.toString(ex.getMessage(),"")));}
 }
 @PostMapping("/cases/{id}/case-cut") ResponseEntity<?> caseCut(@PathVariable Long id, @RequestParam(defaultValue="existing") String dataset, Authentication a){
  AppUser u=me(a);if(!canCasework(u))return ResponseEntity.status(403).build();LegalCase c=cases.findByIdAndOwnerId(id,u.id).orElse(null);if(c==null)return ResponseEntity.notFound().build();
  try{
   Map<String,Object> req=Map.of("query",c.title+"\n"+c.facts,"case_id",c.id,"category",c.category,"report","case_cut","dataset",dataset.equals("madras")?"madras":"existing");
   Map result=http.postForObject(aiUrl+"/case-cut",req,Map.class);if(result==null)return ResponseEntity.status(503).body(Map.of("error","No Case Cut returned."));
   CaseCut cc=new CaseCut();cc.caseId=id;cc.ownerId=u.id;cc.reportJson=new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result);cuts.save(cc);audit(u,"CASE_CUT_GENERATED","CASE_CUT",cc.id);return ResponseEntity.ok(Map.of("id",cc.id,"report",result));
  }catch(Exception ex){return ResponseEntity.status(503).body(Map.of("error","Case Cut service unavailable or report generation failed.","detail",Objects.toString(ex.getMessage(),"")));}
 }
 @GetMapping("/research") ResponseEntity<?> research(@RequestParam String q, @RequestParam(defaultValue="existing") String dataset, Authentication a){if(q.trim().length()<3)return ResponseEntity.badRequest().body(Map.of("error","Enter at least 3 characters."));try{return ResponseEntity.ok(http.getForObject(aiUrl+"/research?q={q}&dataset={dataset}",Map.class,q,dataset.equals("madras")?"madras":"existing"));}catch(Exception e){return ResponseEntity.status(503).body(Map.of("error","Research service unavailable; verify AI service and dataset status."));}}
 @GetMapping("/research/corpus") ResponseEntity<?> corpus(Authentication a){try{return ResponseEntity.ok(http.getForObject(aiUrl+"/corpus/status",Map.class));}catch(Exception e){return ResponseEntity.status(503).body(Map.of("status","UNAVAILABLE","records",0));}}
 @GetMapping("/activity") List<Map<String,Object>> activity(Authentication a){AppUser u=me(a);return audits.findTop100ByActorIdOrderByCreatedAtDesc(u.id).stream().map(e->Map.<String,Object>of("id",e.id,"action",e.action,"resourceType",Objects.toString(e.resourceType,""),"resourceId",Objects.toString(e.resourceId,""),"createdAt",e.createdAt)).toList();}
 @GetMapping("/admin/overview") ResponseEntity<?> admin(Authentication a){AppUser u=me(a);if(!"ADMIN".equals(u.role))return ResponseEntity.status(403).build();return ResponseEntity.ok(Map.of("users",users.count(),"lawyersPending",users.countByRole("LAWYER"),"cases",cases.count(),"caseCuts",cuts.count(),"corpus",safeCorpus(),"recentAudit",audits.findTop200ByOrderByCreatedAtDesc().stream().limit(12).map(e->Map.of("action",e.action,"resource",Objects.toString(e.resourceType,""),"at",e.createdAt)).toList()));}
 @GetMapping("/admin/users") ResponseEntity<?> adminUsers(Authentication a){if(!"ADMIN".equals(me(a).role))return ResponseEntity.status(403).build();return ResponseEntity.ok(users.findAll().stream().map(this::userView).toList());}
 @PutMapping("/admin/users/{id}") ResponseEntity<?> updateUser(@PathVariable Long id,@RequestBody Map<String,String>b,Authentication a){AppUser admin=me(a);if(!"ADMIN".equals(admin.role))return ResponseEntity.status(403).build();AppUser u=users.findById(id).orElse(null);if(u==null)return ResponseEntity.notFound().build();if(b.containsKey("role")&&Set.of("PUBLIC","LAWYER","ADMIN").contains(b.get("role")))u.role=b.get("role");if(b.containsKey("status")&&Set.of("ACTIVE","PENDING","DISABLED").contains(b.get("status")))u.status=b.get("status");users.save(u);audit(admin,"USER_UPDATED","USER",id);return ResponseEntity.ok(userView(u));}
 boolean canCasework(AppUser u){return Set.of("LAWYER","ADMIN").contains(u.role);}
 Map<String,Object> safeCorpus(){
  try {
   Map<?,?> result=http.getForObject(aiUrl+"/corpus/status",Map.class);
   if(result==null)return Map.of("status","UNAVAILABLE");
   Map<String,Object> response=new LinkedHashMap<>();
   for(Map.Entry<?,?> entry:result.entrySet())response.put(String.valueOf(entry.getKey()),entry.getValue());
   return response;
  }catch(Exception e){return Map.of("status","UNAVAILABLE");}
 }
 Map<String,Object> caseView(LegalCase c){
  Map<String,Object> view=new LinkedHashMap<>();
  view.put("id",c.id);view.put("title",c.title);view.put("facts",c.facts);
  view.put("category",Objects.toString(c.category,"PROPERTY"));view.put("stage",Objects.toString(c.stage,""));
  view.put("relief",Objects.toString(c.relief,""));view.put("district",Objects.toString(c.district,""));
  view.put("taluk",Objects.toString(c.taluk,""));view.put("village",Objects.toString(c.village,""));
  view.put("surveyNumber",Objects.toString(c.surveyNumber,""));view.put("propertyType",Objects.toString(c.propertyType,""));
  view.put("status",c.status);view.put("createdAt",c.createdAt);view.put("updatedAt",c.updatedAt);
  return view;
 }
 static String val(Map<String,String>b,String k){return Objects.toString(b.get(k),"").trim();}static String nullable(Object v){String s=Objects.toString(v,"").trim();return s.isBlank()?null:s;}
}
