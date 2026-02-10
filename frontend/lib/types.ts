export type Resource = {
  url: string;
  title: string;
  description: string;
};

export type Log = {
  message: string;
  done: boolean;
};

export type ThinkingStep = {
  type: "analysis" | "execution";
  message: string;
  status: "active" | "completed";
};

export type PlanTask = {
  id: string;
  name: string;
  toolName: string;
  status: "pending" | "running" | "completed" | "error";
};

export type AgentState = {
  model: string;

  // Research-canvas fields
  research_question: string;
  report: string;
  resources: Resource[];

  // Shared logs
  logs: Log[];

  // MCP-specific fields
  thinking_step?: ThinkingStep;
  execution_plan?: PlanTask[];
};