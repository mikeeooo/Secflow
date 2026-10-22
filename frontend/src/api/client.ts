import type {Account,AccountProfile,Assessment,Evaluation,Event,Finding,Overview,Page,PaymentRequest,Transaction,TransactionDetail} from './types'
const base=(import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/,'')
export class ApiError extends Error {constructor(public status:number,message:string){super(message)}}
async function call<T>(path:string,options:RequestInit={}) : Promise<T> {
  let response:Response
  try {response=await fetch(`${base}${path}`,{...options,headers:{'Content-Type':'application/json',...options.headers}})} catch {throw new ApiError(0,'API indisponibil. Datele afișate pot fi vechi. Reîncearcă.')}
  if(!response.ok){let detail='Cererea nu a putut fi procesată';try{const body=await response.json();detail=typeof body.detail==='string'?body.detail:detail}catch{}throw new ApiError(response.status,detail)}
  return response.json() as Promise<T>
}
function qs(params:Record<string,string|number|undefined>){const values=new URLSearchParams();Object.entries(params).forEach(([k,v])=>{if(v!==undefined&&v!=='')values.set(k,String(v))});return values.toString()}
export const api={
  health:()=>call<{status:string;model_version:string|null;model_error:string|null}>('/health'),
  overview:(params:Record<string,string|undefined>={})=>call<Overview>(`/overview?${qs(params)}`),
  transactions:(params:Record<string,string|number|undefined>)=>call<Page<Transaction>>(`/transactions?${qs(params)}`),
  transaction:(id:string)=>call<TransactionDetail>(`/transactions/${encodeURIComponent(id)}`),
  accounts:(params:Record<string,string|number|undefined>={})=>call<Page<Account>>(`/accounts?${qs(params)}`),
  account:(id:string)=>call<AccountProfile>(`/accounts/${encodeURIComponent(id)}`),
  accountActivity:(id:string,page=1)=>call<Page<Event>>(`/accounts/${encodeURIComponent(id)}/activity?${qs({page,page_size:20})}`),
  findings:(account_id?:string)=>call<Page<Finding>>(`/batch-findings?${qs({page:1,page_size:100,account_id})}`),
  experiments:()=>call<Evaluation>('/experiments'),
  createSession:(local_account_id:string,device_id:string)=>call<{session_id:string}>('/sessions',{method:'POST',body:JSON.stringify({local_account_id,device_id})}),
  prepareContext:(local_account_id:string)=>call<{attempts_created:number}>('/demo/context',{method:'POST',body:JSON.stringify({local_account_id,attempt_count:5})}),
  createAssessment:(payload:PaymentRequest)=>call<Assessment>('/assessments',{method:'POST',body:JSON.stringify(payload)}),
  review:(id:string,action:'approve'|'reject',note:string)=>call<Assessment>(`/assessments/${encodeURIComponent(id)}/reviews`,{method:'POST',body:JSON.stringify({action,note})})
}
