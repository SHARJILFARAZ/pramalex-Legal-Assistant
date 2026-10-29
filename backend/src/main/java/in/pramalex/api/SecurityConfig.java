package in.pramalex.api;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import org.springframework.context.annotation.*;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.*;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.filter.OncePerRequestFilter;
import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.List;

@Configuration
class SecurityConfig {
 @Bean PasswordEncoder passwordEncoder(){return new BCryptPasswordEncoder();}
 @Bean org.springframework.web.cors.CorsConfigurationSource corsConfigurationSource(){
  var c=new org.springframework.web.cors.CorsConfiguration();
  c.setAllowedOrigins(List.of("http://localhost:5173","http://127.0.0.1:5173"));
  c.setAllowedMethods(List.of("GET","POST","PUT","PATCH","DELETE","OPTIONS"));
  c.setAllowedHeaders(List.of("Authorization","Content-Type"));
  c.setAllowCredentials(true);
  var source=new org.springframework.web.cors.UrlBasedCorsConfigurationSource();
  source.registerCorsConfiguration("/**",c); return source;
 }
 @Bean SecurityFilterChain filterChain(HttpSecurity http, TokenFilter filter) throws Exception {
  return http.csrf(c->c.disable()).cors(c->{}).sessionManagement(s->s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
   .authorizeHttpRequests(a->a.requestMatchers("/api/auth/**","/api/health","/error").permitAll().anyRequest().authenticated())
   .addFilterBefore(filter,UsernamePasswordAuthenticationFilter.class).build();
 }
}
@org.springframework.stereotype.Component
class TokenService {
 private final SecretKey key;
 TokenService(@org.springframework.beans.factory.annotation.Value("${pramalex.jwt.secret}") String secret) {
  if(secret.length()<32) throw new IllegalStateException("JWT_SECRET must be at least 32 characters");
  key=Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
 }
 String issue(AppUser u){return Jwts.builder().subject(u.id.toString()).claim("role",u.role).claim("email",u.email).issuedAt(new java.util.Date()).expiration(new java.util.Date(System.currentTimeMillis()+86400000L)).signWith(key).compact();}
 Claims parse(String token){return Jwts.parser().verifyWith(key).build().parseSignedClaims(token).getPayload();}
}
@org.springframework.stereotype.Component
class TokenFilter extends OncePerRequestFilter {
 private final TokenService tokens; private final UserRepo users;
 TokenFilter(TokenService t,UserRepo u){tokens=t;users=u;}
 @Override protected void doFilterInternal(HttpServletRequest req,HttpServletResponse res,FilterChain chain)throws ServletException,java.io.IOException{
  String h=req.getHeader("Authorization");
  if(h!=null&&h.startsWith("Bearer ")) try{
   Claims c=tokens.parse(h.substring(7)); Long id=Long.valueOf(c.getSubject());
   AppUser u=users.findById(id).orElse(null);
   if(u!=null&&"ACTIVE".equals(u.status)){
    var auth=new UsernamePasswordAuthenticationToken(u.id.toString(),null,List.of(new SimpleGrantedAuthority("ROLE_"+u.role)));
    auth.setDetails(u);SecurityContextHolder.getContext().setAuthentication(auth);
   }
  }catch(Exception ignored){SecurityContextHolder.clearContext();}
  chain.doFilter(req,res);
 }
}
