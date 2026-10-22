import {useCallback,useEffect,useRef,useState} from 'react'
export function useLiveData<T>(load:()=>Promise<T>,interval=0){
 const [data,setData]=useState<T|null>(null),[error,setError]=useState<string|null>(null),[loading,setLoading]=useState(true),[updated,setUpdated]=useState<string|null>(null)
 const active=useRef(true)
 const revision=useRef(0)
 const refresh=useCallback(async()=>{const ticket=++revision.current;try{const result=await load();if(active.current&&ticket===revision.current){setData(result);setError(null);setUpdated(new Date().toISOString())}}catch(e){if(active.current&&ticket===revision.current)setError(e instanceof Error?e.message:'Eroare necunoscută')}finally{if(active.current&&ticket===revision.current)setLoading(false)}},[load])
 useEffect(()=>{active.current=true;setLoading(true);setData(null);void refresh();return()=>{active.current=false;revision.current++}},[refresh])
 useEffect(()=>{if(!interval)return;const timer=window.setInterval(()=>{if(document.visibilityState==='visible')void refresh()},interval);return()=>window.clearInterval(timer)},[interval,refresh])
 return {data,error,loading,updated,refresh}
}
