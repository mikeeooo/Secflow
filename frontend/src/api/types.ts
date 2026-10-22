export type Decision = 'Permit'|'Verify'|'Block'|'Pending'
export type PaymentStatus = 'completed'|'awaiting_review'|'blocked'|'pending'|'attempt_only'
export interface Reason {code:string;detail:string;[key:string]:unknown}
export interface RiskResult {score:number;decision:Decision;reasons:Reason[];if_percentile:number|null;lof_percentile:number|null;rule_score:number|null;model_version:string|null;policy_version:string}
export interface PaymentRequest {transaction_id:string;sender_account_id:string;receiver_account_id:string;receiver_psp:string;amount_bani:number;currency:'MDL';session_id:string;device_id:string;initiation_method:'APP'|'ALIAS'}
export interface Assessment {transaction_id:string;scored_at:string;request:PaymentRequest;feature_snapshot:Record<string,number>;result:RiskResult;processing_ms:number;mock_submitted:boolean;payment_status:PaymentStatus;review_status:string;review_actions?:ReviewAction[]}
export interface ReviewAction {action:string;note:string;acted_at:string;actor?:string}
export interface Transaction {transaction_id:string;event_type:string;observed_at:string;sender_account_id:string;receiver_account_id:string;receiver_psp:string;amount_bani:number;currency:string;session_id:string;decision:Decision|null;score:number|null;historical:boolean;payment_status:PaymentStatus;review_status:string}
export interface Event {transaction_id:string;event_type:string;observed_at:string;sender_account_id:string;receiver_account_id:string;receiver_psp:string;amount_bani:number;currency:string;session_id:string}
export interface Finding {window_end:string;available_at:string;noise_flag:boolean;cluster_label?:number;contextual_rule_flags:string[];account_id?:string}
export interface TransactionDetail {transaction:Event;assessment:Assessment|null;timeline:Event[];review_actions:ReviewAction[];batch_finding:Finding|null}
export interface Page<T> {items:T[];total:number;page:number;page_size:number}
export interface Overview {simulation:boolean;accounts:number;historical_requests:number;assessments:number;pending_reviews:number;decision_counts:Record<Decision,number>;daily_attempts:{day:string;count:number}[];recent:Assessment[];model_version:string|null;updated_at:string}
export interface Account {account_id:string;balance_bani:number;opened_at:string}
export interface AccountProfile extends Account {incoming_bani:number;outgoing_bani:number;counterparties:string[];findings:Finding[]}
export interface Evaluation {simulation:boolean;test_range:string;test_rows:number;test_labels:number;observed_test_prevalence:number;model_version:string;methods:Record<string,{precision:number;recall:number;f1:number;false_positive_rate:number;alert_volume:number;tp:number;fp:number;fn:number;tn:number}>;per_scenario:Record<string,{cases:number;detected:number;recall:number}>;api_benchmark:{p95_ms:number;measurement:string};evaluation_notes:string[];status?:string}
