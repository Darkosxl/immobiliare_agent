export interface CallLog {
    id: string
    status: string
    startedAt: string
    endedAt: string
    cost: number
    analysis?: {
        summary?: string
        successEvaluation?: string
    }
    artifact?: {
        recordingUrl?: string
        transcript?: string
        messages?: Array<{
            role: string
            message?: string
            tool_calls?: Array<{
                type: string
                function: {
                    name: string
                    arguments: string
                }
            }>
            function_call?: {
                name: string
                arguments: string
            }
            tool_call_id?: string
        }>
    }
    assistant?: {
        firstMessage?: string
    }
    customer?: {
        number?: string
    }
}

export interface GoogleToken {
    access_token: string
    refresh_token?: string
    scope: string
    token_type: string
    expiry_date?: number
    expires_in?: number
}
