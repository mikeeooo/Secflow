import {useEffect,useRef,useState,type KeyboardEvent} from 'react'
import {NavLink,Route,Routes,useLocation} from 'react-router-dom'
import {Activity,ChartNoAxesCombined,ChevronRight,LayoutDashboard,ListFilter,Menu,UsersRound,WalletCards,X} from 'lucide-react'
import {OverviewPage} from './pages/Overview'
import {TransactionsPage} from './pages/Transactions'
import {InvestigationPage} from './pages/Investigation'
import {AccountsPage,AccountPage} from './pages/Accounts'
import {SimulatorPage} from './pages/Simulator'
import {EvaluationPage} from './pages/Evaluation'

const nav=[{to:'/',label:'Prezentare generală',icon:LayoutDashboard},{to:'/transactions',label:'Tranzacții',icon:ListFilter},{to:'/accounts',label:'Conturi locale',icon:UsersRound},{to:'/simulator',label:'Simulator de plată',icon:WalletCards},{to:'/evaluation',label:'Evaluare modele',icon:ChartNoAxesCombined}]
const title=(path:string)=>path.startsWith('/transactions/')?'Investigație':path.startsWith('/transactions')?'Tranzacții':path.startsWith('/accounts/')?'Profil cont':path.startsWith('/accounts')?'Conturi locale':path.startsWith('/simulator')?'Simulator de plată':path.startsWith('/evaluation')?'Evaluare modele':'Prezentare generală'

export default function App(){
 const [open,setOpen]=useState(false)
 const location=useLocation()
 const asideRef=useRef<HTMLElement>(null)
 const firstNavRef=useRef<HTMLAnchorElement>(null)
 const menuButtonRef=useRef<HTMLButtonElement>(null)
 const mainRef=useRef<HTMLElement>(null)
 const hadOpen=useRef(false)
 const focusAfterClose=useRef<'menu'|'main'>('menu')

 const closeMenu=(focus:'menu'|'main'='menu')=>{focusAfterClose.current=focus;setOpen(false)}

 useEffect(()=>{
  if(open){hadOpen.current=true;firstNavRef.current?.focus()}
  else if(hadOpen.current){
   if(focusAfterClose.current==='main') mainRef.current?.focus()
   else menuButtonRef.current?.focus()
   hadOpen.current=false
  }
 },[open])

 useEffect(()=>{
  if(!open)return
  const onEscape=(event:globalThis.KeyboardEvent)=>{if(event.key==='Escape'){event.preventDefault();closeMenu()}}
  window.addEventListener('keydown',onEscape)
  return ()=>window.removeEventListener('keydown',onEscape)
 },[open])

 const trapMenuFocus=(event:KeyboardEvent<HTMLElement>)=>{
  if(!open||event.key!=='Tab')return
  const focusable=asideRef.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')
  if(!focusable?.length)return
  const first=focusable[0],last=focusable[focusable.length-1]
  if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
  else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
 }

 return <div className="app-shell">
 <a className="skip-link" href="#main">Sari la conținut</a>
 {open&&<button className="mobile-scrim" tabIndex={-1} aria-label="Închide meniul" onClick={()=>closeMenu()}/>}
 <aside ref={asideRef} className={`sidebar ${open?'sidebar-open':''}`} aria-label="Navigație principală" role={open?'dialog':undefined} aria-modal={open||undefined} onKeyDown={trapMenuFocus}>
  <div className="brand"><img className="brand-mark" src="/secflow-mark.svg" width="32" height="32" alt=""/><div><strong>SecFlow</strong><span>Analiza plăților MIA</span></div><button className="nav-close" aria-label="Închide meniul" onClick={()=>closeMenu()}><X size={20}/></button></div>
  <nav>{nav.map((item,index)=><NavLink ref={index===0?firstNavRef:undefined} key={item.to} to={item.to} end={item.to==='/'} onClick={()=>closeMenu('main')} className={({isActive})=>`nav-item ${isActive?'active':''}`}><item.icon size={18}/><span>{item.label}</span></NavLink>)}</nav>
  <div className="sidebar-bottom"><div className="sidebar-help">Proiect universitar <ChevronRight size={15}/></div><div className="sidebar-info"><Activity size={15}/><div><strong>Simulare locală</strong><span>Portofoliu fictiv · fără plăți reale</span></div></div></div>
 </aside>
 <div className="workspace" inert={open}>
  <header className="topbar"><button ref={menuButtonRef} className="menu-toggle" aria-label="Deschide meniul" aria-expanded={open} onClick={()=>setOpen(true)}><Menu size={20}/></button><div className="topbar-brand"><img src="/secflow-mark.svg" width="24" height="24" alt=""/><strong>SecFlow</strong><span aria-hidden="true">/</span></div><div className="breadcrumb"><span>MIA · Plăți instant simulate</span><ChevronRight size={15}/><strong>{title(location.pathname)}</strong></div><div className="topbar-right"><span className="environment-badge"><span/> Simulare</span><span className="topbar-date">Sistem local · MDL</span></div></header>
  <main ref={mainRef} id="main" tabIndex={-1} className="main-content"><Routes><Route path="/" element={<OverviewPage/>}/><Route path="/transactions" element={<TransactionsPage/>}/><Route path="/transactions/:transactionId" element={<InvestigationPage/>}/><Route path="/accounts" element={<AccountsPage/>}/><Route path="/accounts/:accountId" element={<AccountPage/>}/><Route path="/simulator" element={<SimulatorPage/>}/><Route path="/evaluation" element={<EvaluationPage/>}/></Routes></main>
 </div></div>
}
