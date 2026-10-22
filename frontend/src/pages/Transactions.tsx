import {useCallback,useState} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {ArrowUpRight,ChevronLeft,ChevronRight,Search,SlidersHorizontal} from 'lucide-react'
import {api} from '../api/client'
import {useLiveData} from '../hooks'
import {dateTime,money} from '../lib-utils'
import {localDayUtcBounds} from '../date-range'
import {Card} from '../components/ui/card'
import {Input} from '../components/ui/input'
import {Button} from '../components/ui/button'
import {DataState,DecisionBadge,LastUpdate,PaymentBadge,ReviewBadge,SectionHeading,StaleBanner} from '../components/shared'

export function TransactionsPage(){
  const [params,setParams]=useSearchParams()
  const value=(name:string,defaultValue='')=>params.get(name)||defaultValue
  const page=Math.max(1,Number(value('page','1'))||1)
  const search=value('search'),decision=value('decision'),sort_by=value('sort_by','time'),sort_dir=value('sort_dir','desc')
  const from=value('from'),to=value('to'),min=value('min'),max=value('max')
  const advancedActive=Boolean(min||max||sort_by!=='time'||sort_dir!=='desc')
  const [advancedOpen,setAdvancedOpen]=useState(advancedActive)
  const patch=(changes:Record<string,string>)=>{
    const next=new URLSearchParams(params)
    Object.entries(changes).forEach(([key,item])=>item?next.set(key,item):next.delete(key))
    if(!('page' in changes))next.delete('page')
    setParams(next)
  }
  const loader=useCallback(()=>api.transactions({
    page,page_size:20,search,decision,sort_by,sort_dir,
    from_date:from?localDayUtcBounds(from).start:undefined,
    to_date:to?localDayUtcBounds(to).end:undefined,
    min_amount_bani:min?Math.round(Number(min)*100):undefined,
    max_amount_bani:max?Math.round(Number(max)*100):undefined,
  }),[page,search,decision,sort_by,sort_dir,from,to,min,max])
  const {data,error,loading,updated,refresh}=useLiveData(loader,5000)
  return <>
    <div className="page-head"><div><h1>Tranzacții</h1><p>Caută o încercare de plată și urmărește decizia în context.</p></div><LastUpdate value={updated} onRefresh={()=>void refresh()}/></div>
    <StaleBanner error={error&&data?error:null}/>
    <Card className="filter-card">
      <div className="filter-top"><div className="filter-title"><SlidersHorizontal size={17}/> Filtrează fluxul</div><div className="filter-count" aria-live="polite">{data?`${data.total.toLocaleString('ro-MD')} rezultate`:'Se încarcă'}</div></div>
      <div className="filter-grid filter-primary">
        <label className="field search-field"><span>Căutare tranzacție sau cont</span><div className="input-icon"><Search size={17}/><Input value={search} onChange={e=>patch({search:e.target.value})} placeholder="ID tranzacție sau cont"/></div></label>
        <label className="field"><span>Decizie</span><select value={decision} onChange={e=>patch({decision:e.target.value})}><option value="">Toate</option><option>Permit</option><option>Verify</option><option>Block</option><option>Pending</option></select></label>
        <label className="field"><span>De la</span><Input type="date" value={from} onChange={e=>patch({from:e.target.value})}/></label>
        <label className="field"><span>Până la</span><Input type="date" value={to} onChange={e=>patch({to:e.target.value})}/></label>
      </div>
      <details className="advanced-filters" open={advancedOpen} onToggle={event=>setAdvancedOpen(event.currentTarget.open)}>
        <summary>Mai multe filtre{advancedActive?' · active':''}</summary>
        <div className="filter-grid filter-secondary">
          <label className="field"><span>Sumă minimă · MDL</span><Input type="number" min="0" value={min} onChange={e=>patch({min:e.target.value})}/></label>
          <label className="field"><span>Sumă maximă · MDL</span><Input type="number" min="0" value={max} onChange={e=>patch({max:e.target.value})}/></label>
          <label className="field"><span>Ordonează după</span><select value={sort_by} onChange={e=>patch({sort_by:e.target.value})}><option value="time">Moment</option><option value="amount">Sumă</option><option value="score">Scor risc</option></select></label>
          <label className="field"><span>Ordine</span><select value={sort_dir} onChange={e=>patch({sort_dir:e.target.value})}><option value="desc">Descrescător</option><option value="asc">Crescător</option></select></label>
        </div>
      </details>
    </Card>
    <DataState loading={loading} error={error} hasData={!!data} onRetry={()=>void refresh()}/>
    {data&&<Card className="ledger-card"><div className="card-pad">
      <SectionHeading title="Încercări observate" detail="Rândurile istorice fără evaluare live sunt marcate separat."/>
      {data.items.length?<><div className="table-wrap"><table className="data-table transactions-table"><thead><tr><th>Moment / ID</th><th className="hide-mobile">Expeditor</th><th className="hide-mobile">Destinatar</th><th>Sumă</th><th className="hide-mobile">Scor</th><th>Decizie</th><th className="hide-mobile">Plată</th><th className="hide-mobile">Revizuire</th><th aria-label="Detalii"></th></tr></thead><tbody>{data.items.map(row=><tr key={row.transaction_id}>
        <td><Link className="row-link" to={`/transactions/${encodeURIComponent(row.transaction_id)}`}>{row.transaction_id}</Link><div className="cell-sub">{dateTime(row.observed_at)}</div><div className="mobile-row-context">{row.sender_account_id} → {row.receiver_account_id}</div></td>
        <td className="hide-mobile">{row.sender_account_id}</td><td className="hide-mobile">{row.receiver_account_id}<div className="cell-sub">{row.receiver_psp}</div></td>
        <td className="money-cell">{money(row.amount_bani)}</td><td className="hide-mobile">{row.score===null?'—':Math.round(row.score)}</td><td><DecisionBadge value={row.decision}/></td><td className="hide-mobile"><PaymentBadge value={row.payment_status}/></td><td className="hide-mobile"><ReviewBadge value={row.review_status}/></td><td><Link className="table-action" to={`/transactions/${encodeURIComponent(row.transaction_id)}`} aria-label={`Deschide tranzacția ${row.transaction_id}`}><ArrowUpRight size={17}/></Link></td>
      </tr>)}</tbody></table></div>
      <div className="mobile-transaction-list">{data.items.map(row=><Link className="mobile-transaction" key={row.transaction_id} to={`/transactions/${encodeURIComponent(row.transaction_id)}`}>
        <span className="mobile-transaction-head"><strong>{row.transaction_id}</strong><b>{money(row.amount_bani)}</b></span>
        <span className="mobile-transaction-meta"><span>{dateTime(row.observed_at)}</span><DecisionBadge value={row.decision}/></span>
        <span className="mobile-transaction-route">{row.sender_account_id} → {row.receiver_account_id}</span>
      </Link>)}</div></>:<div className="empty-inline"><Search size={25}/><strong>Nicio tranzacție pentru filtrele alese</strong><span>Schimbă termenul sau intervalul selectat.</span><Button variant="outline" onClick={()=>setParams(new URLSearchParams())}>Șterge filtrele</Button></div>}
      <div className="pagination"><span>Pagina {data.page} din {Math.max(1,Math.ceil(data.total/data.page_size))} · {data.total} rezultate</span><div><Button variant="outline" size="sm" disabled={page<=1} onClick={()=>patch({page:String(page-1)})}><ChevronLeft size={16}/> Anterior</Button><Button variant="outline" size="sm" disabled={page*data.page_size>=data.total} onClick={()=>patch({page:String(page+1)})}>Următor <ChevronRight size={16}/></Button></div></div>
    </div></Card>}
  </>
}
