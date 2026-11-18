export interface AnalysisTotal {
  users: number
  documents: number
  versions: number
  operation_logs: number
}

export interface WeeklyUserActivity {
  value: number
  name: string
}

export interface MonthlySales {
  name: string
  estimate: number
  actual: number
}
