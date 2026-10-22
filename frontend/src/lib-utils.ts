import {clsx,type ClassValue} from 'clsx'
import {twMerge} from 'tailwind-merge'
export const cn=(...inputs:ClassValue[])=>twMerge(clsx(inputs))
export const money=(bani:number)=>new Intl.NumberFormat('ro-MD',{minimumFractionDigits:2,maximumFractionDigits:2}).format(bani/100)+' MDL'
export const dateTime=(value:string)=>new Intl.DateTimeFormat('ro-MD',{dateStyle:'medium',timeStyle:'short',timeZone:'Europe/Chisinau'}).format(new Date(value))+' · Chișinău'
export const pct=(value:number)=>new Intl.NumberFormat('ro-MD',{style:'percent',maximumFractionDigits:1}).format(value)
