const BASE=import.meta.env.VITE_API_URL||'http://localhost:8080/api';
export type User={id:number;email:string;fullName:string;role:'PUBLIC'|'LAWYER'|'ADMIN';status:string};
export function token(){return localStorage.getItem('pl_token')||''}
export function saveSession(t:string,u:User){localStorage.setItem('pl_token',t);localStorage.setItem('pl_user',JSON.stringify(u))}
export function getUser():User|null{try{return JSON.parse(localStorage.getItem('pl_user')||'null')}catch{return null}}
export function clearSession(){localStorage.removeItem('pl_token');localStorage.removeItem('pl_user')}
export async function api(path:string,options:RequestInit={}){const headers=new Headers(options.headers||{});if(token())headers.set('Authorization',`Bearer ${token()}`);if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json');const res=await fetch(BASE+path,{...options,headers});const data=await res.json().catch(()=>({}));if(!res.ok)throw new Error(data.error||data.message||`Request failed (${res.status})`);return data}
export const post=(p:string,b:any)=>api(p,{method:'POST',body:JSON.stringify(b)});
