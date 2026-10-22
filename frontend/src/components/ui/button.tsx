import {forwardRef} from 'react'
import {cva,type VariantProps} from 'class-variance-authority'
import {cn} from '../../lib-utils'
const styles=cva('btn',{variants:{variant:{default:'btn-primary',secondary:'btn-secondary',outline:'btn-outline',danger:'btn-danger',ghost:'btn-ghost'},size:{default:'btn-default',sm:'btn-sm',icon:'btn-icon'}},defaultVariants:{variant:'default',size:'default'}})
type Props=React.ButtonHTMLAttributes<HTMLButtonElement>&VariantProps<typeof styles>
export const Button=forwardRef<HTMLButtonElement,Props>(({className,variant,size,...props},ref)=><button ref={ref} className={cn(styles({variant,size}),className)} {...props}/>);Button.displayName='Button'
