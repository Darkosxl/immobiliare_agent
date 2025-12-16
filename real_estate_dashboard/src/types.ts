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
