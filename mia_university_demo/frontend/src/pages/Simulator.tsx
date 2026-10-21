import {useCallback,useState} from 'react'
import {Link} from 'react-router-dom'
import {ArrowRight,CheckCircle2,Info,RotateCcw,Send,ShieldAlert} from 'lucide-react'
import {api} from '../api/client'
import type {Assessment} from '../api/types'
import {useLiveData} from '../hooks'
import {money} from '../lib-utils'
import {Card} from '../components/ui/card'
import {Button} from '../components/ui/button'
import {Input} from '../components/ui/input'
import {DataState,DecisionBadge,PaymentBadge,SectionHeading} from '../components/shared'

const newId=()=>`DEMO-${crypto.randomUUID().slice(0,12).toUpperCase()}`
const externalId=(kind:string)=>`EXT-${kind}-${crypto.randomUUID().slice(0,8).toUpperCase()}`

export function SimulatorPage(){
  const load=useCallback(()=>api.accounts({page:1,page_size:100}),[])
  const {data,error:accountsError,loading,refresh}=useLiveData(load)
  const [sender,setSender]=useState('')
  const [receiver,setReceiver]=useState('')
  const [externalReceiver,setExternalReceiver]=useState('EXT-DEMO-001')
  const [receiverPsp,setReceiverPsp]=useState('LOCAL')
  const [amount,setAmount]=useState('150.00')
  const [device,setDevice]=useState('known')
  const [method,setMethod]=useState<'APP'|'ALIAS'>('APP')
  const [draftId,setDraftId]=useState(newId)
  const [sessionId,setSessionId]=useState('')
  const [attempted,setAttempted]=useState(false)
  const [busy,setBusy]=useState(false)
  const [result,setResult]=useState<Assessment|null>(null)
  const [submitError,setSubmitError]=useState<string|null>(null)
  const [contextStatus,setContextStatus]=useState<string|null>(null)
  const [preset,setPreset]=useState<'normal'|'unusual'|'high'|null>(null)
  const accounts=data?.items||[]
  const selectedSender=sender||accounts[0]?.account_id||''
  const selectedReceiver=receiverPsp==='LOCAL'?(receiver||accounts.find(a=>a.account_id!==selectedSender)?.account_id||''):externalReceiver
  const deviceId=device==='known'?`MAIN-${selectedSender}`:`NEW-DEMO-${selectedSender}`

  function reset(){setDraftId(newId());setSessionId('');setAttempted(false);setResult(null);setSubmitError(null);setContextStatus(null);setPreset(null)}
  function chooseNormal(){setPreset('normal');setReceiverPsp('LOCAL');setAmount('150.00');setDevice('known');setContextStatus(null);setSubmitError(null)}
  function chooseUnusual(){setPreset('unusual');setReceiverPsp('PSP-1');setExternalReceiver(externalId('DEMO'));setAmount('1000.00');setDevice('known');setContextStatus(null);setSubmitError(null)}
  async function chooseHigh(){
    if(!selectedSender||busy||attempted)return
    setBusy(true);setSubmitError(null)
    try{
      const context=await api.prepareContext(selectedSender)
      setPreset('high');setReceiverPsp('PSP-1');setExternalReceiver(externalId('RISK'))
      setAmount('1000.00');setDevice('new')
      setContextStatus(`${context.attempts_created} încercări anterioare au fost observate pentru ${selectedSender}. Plata încă nu a fost trimisă.`)
    }catch(error){setSubmitError(error instanceof Error?error.message:'Nu s-a putut pregăti scenariul')}
    finally{setBusy(false)}
  }
  async function submit(event:React.FormEvent){
    event.preventDefault()
    if(busy||result)return
    setSubmitError(null);setBusy(true);setAttempted(true)
    try{
      if(!selectedSender||!selectedReceiver)throw new Error('Pregătește conturile demo sau alege expeditorul și destinatarul.')
      const amount_bani=Math.round(Number(amount)*100)
      if(!Number.isFinite(amount_bani)||amount_bani<=0)throw new Error('Introdu o sumă pozitivă.')
      let currentSession=sessionId
      if(!currentSession){currentSession=(await api.createSession(selectedSender,deviceId)).session_id;setSessionId(currentSession)}
      const response=await api.createAssessment({transaction_id:draftId,sender_account_id:selectedSender,receiver_account_id:selectedReceiver,receiver_psp:receiverPsp,amount_bani,currency:'MDL',session_id:currentSession,device_id:deviceId,initiation_method:method})
      setResult(response)
    }catch(error){setSubmitError(error instanceof Error?error.message:'Cererea a eșuat')}
    finally{setBusy(false)}
  }
  return <>
    <div className="page-head"><div><div className="eyebrow">LABORATORUL DE DECIZII</div><h1>Simulator de plată</h1><p>Testează fluxul complet: observații → caracteristici → modele și reguli → decizie.</p></div></div>
    <div className="notice"><Info size={18}/> Toate operațiile sunt locale și simulate. Nu se trimit plăți reale; eticheta ascunsă de fraudă nu este introdusă în formular.</div>
    <div className="sim-grid"><Card><div className="card-pad">
      <SectionHeading title="Detaliile plății" detail="Serviciul API calculează singur istoricul și scorul. ID-ul rămâne același la reîncercarea unei cereri incerte."/>
      <DataState loading={loading} error={accountsError} hasData={!!data} onRetry={()=>void refresh()}/>
      {data&&<form onSubmit={event=>void submit(event)} className="form-grid">
        <div className="preset-bar"><span>EXEMPLE RAPIDE</span><div><Button type="button" size="sm" variant={preset==='normal'?'secondary':'outline'} disabled={busy||attempted} onClick={chooseNormal}>Obișnuită</Button><Button type="button" size="sm" variant={preset==='unusual'?'secondary':'outline'} disabled={busy||attempted} onClick={chooseUnusual}>Atipică</Button><Button type="button" size="sm" variant={preset==='high'?'secondary':'outline'} disabled={busy||attempted} onClick={()=>void chooseHigh()}>Viteză mare</Button></div></div>
        <label className="field"><span>Cont expeditor · PSP local</span><select value={selectedSender} disabled={busy||attempted} onChange={event=>{setSender(event.target.value);setReceiver('')}}>{accounts.map(account=><option key={account.account_id} value={account.account_id}>{account.account_id} · {money(account.balance_bani)}</option>)}</select></label>
        <label className="field"><span>Destinatar</span>{receiverPsp==='LOCAL'?<select value={selectedReceiver} disabled={busy||attempted} onChange={event=>setReceiver(event.target.value)}>{accounts.filter(account=>account.account_id!==selectedSender).map(account=><option key={account.account_id} value={account.account_id}>{account.account_id}</option>)}</select>:<Input value={externalReceiver} disabled={busy||attempted} onChange={event=>setExternalReceiver(event.target.value)} minLength={1} required/>}</label>
        <label className="field"><span>PSP destinatar</span><select value={receiverPsp} disabled={busy||attempted} onChange={event=>setReceiverPsp(event.target.value)}><option value="LOCAL">LOCAL · transfer între conturi</option><option value="PSP-1">PSP-1 · cont extern simulat</option></select></label>
        <label className="field"><span>Sumă · MDL</span><Input type="number" min="0.01" step="0.01" value={amount} disabled={busy||attempted} onChange={event=>setAmount(event.target.value)} required/></label>
        <label className="field"><span>Dispozitiv</span><select value={device} disabled={busy||attempted} onChange={event=>setDevice(event.target.value)}><option value="known">Dispozitiv cunoscut</option><option value="new">Dispozitiv nou</option></select></label>
        <label className="field"><span>Inițiere</span><select value={method} disabled={busy||attempted} onChange={event=>setMethod(event.target.value as 'APP'|'ALIAS')}><option value="APP">Aplicație</option><option value="ALIAS">Alias</option></select></label>
        {contextStatus&&<div className="notice form-message" role="status"><Info size={18}/>{contextStatus}</div>}
        <div className="form-footer"><div><span>ID cerere</span><code>{draftId}</code></div><Button type="submit" disabled={busy||!!result||!accounts.length}><Send size={17}/>{busy?'Se evaluează…':submitError&&attempted?'Reîncearcă același ID':'Evaluează plata'}</Button></div>
        {submitError&&<div className="notice warning form-message" role="alert"><ShieldAlert size={18}/><span>{submitError} {attempted?'Datele formularului și ID-ul au fost păstrate.':''}</span></div>}
        {attempted&&<Button variant="outline" type="button" onClick={reset} disabled={busy}><RotateCcw size={16}/> Cerere nouă</Button>}
      </form>}
    </div></Card><div><Card className="result-panel"><div className="card-pad"><SectionHeading title="Rezultatul evaluării" detail="Răspunsul este afișat doar după confirmarea API-ului."/>
      {result?<div className="result-content"><div className={`result-icon ${result.result.decision.toLowerCase()}`}>{result.result.decision==='Permit'?<CheckCircle2 size={26}/>:<ShieldAlert size={26}/>}</div><div className="micro-label">DECIZIE ÎNREGISTRATĂ</div><DecisionBadge value={result.result.decision}/><div className="result-score">{Math.round(result.result.score)}<span>/ 100 · rang de risc</span></div><div className="result-status"><span>Plată</span><PaymentBadge value={result.payment_status}/></div><p>{result.result.decision==='Pending'?result.result.reasons.map(reason=>reason.detail).join(' '):'Evaluarea a fost salvată. Decizia originală rămâne disponibilă pentru investigație.'}</p><Link className="btn btn-primary btn-default" to={`/transactions/${encodeURIComponent(result.transaction_id)}`}>Deschide investigația <ArrowRight size={17}/></Link></div>:<div className="empty-result"><div className="empty-result-icon"><ShieldAlert size={30}/></div><strong>Așteptăm o plată de test</strong><p>Completează detaliile și trimite cererea. Aici vei vedea scorul, decizia și starea plății.</p></div>}
    </div></Card><Card className="explain-card"><div className="card-pad"><h3>Ce se întâmplă după trimitere?</h3><ol><li>API-ul verifică cererea și extrage doar istoricul local anterior.</li><li>Isolation Forest și LOF calculează ranguri de anomalie; regulile adaugă motive explicite.</li><li>Decizia și caracteristicile sunt salvate. Permit execută un transfer mock; Verify așteaptă revizuirea.</li></ol></div></Card></div></div>
  </>
}
