"use client";

import { useState, useEffect } from "react";
import { Textarea } from "@/components/ui/textarea";
import {
  useCoAgent,
  useCoAgentStateRender,
  useCopilotAction,
} from "@copilotkit/react-core";
import { Progress } from "./Progress";
import { EditResourceDialog } from "./EditResourceDialog";
import { AddResourceDialog } from "./AddResourceDialog";
import { Resources } from "./Resources";
import { AgentState, Resource } from "@/lib/types";
import { useModelSelectorContext } from "@/lib/model-selector-provider";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Pencil, Eye } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ResearchStateInfo {
  hasData: boolean;
  researchQuestion?: string;
  resourceCount: number;
  hasReport: boolean;
}

interface ResearchCanvasProps {
  /** Callback to notify parent when research state changes (for panel visibility + suggestions) */
  onStateChange?: (info: ResearchStateInfo) => void;
}

export function ResearchCanvas({ onStateChange }: ResearchCanvasProps) {
  const { model, agent } = useModelSelectorContext();

  // Single source of truth for agent state - NO other useCoAgent should exist
  const { state, setState } = useCoAgent<AgentState>({
    name: agent,
    initialState: {
      model,
    },
  });

  // Notify parent about state changes (for panel visibility + chat suggestions)
  useEffect(() => {
    const hasData =
      (state?.resources && state.resources.length > 0) ||
      (state?.report && state.report.trim().length > 0);
    onStateChange?.({
      hasData: !!hasData,
      researchQuestion: state?.research_question,
      resourceCount: state?.resources?.length || 0,
      hasReport: !!(state?.report && state.report.trim().length > 0),
    });
  }, [state?.resources, state?.report, state?.research_question, onStateChange]);

  // Render agent progress in CopilotChat (always active since component is always mounted)
  useCoAgentStateRender({
    name: agent,
    render: ({ state, nodeName, status }) => {
      if (!state.logs || state.logs.length === 0) {
        return null;
      }
      return <Progress logs={state.logs} />;
    },
  });

  // DeleteResources action - always registered since component is always mounted
  useCopilotAction({
    name: "DeleteResources",
    description:
      "Prompt the user for resource delete confirmation, and then perform resource deletion",
    available: "remote",
    parameters: [
      {
        name: "urls",
        type: "string[]",
      },
    ],
    renderAndWait: ({ args, status, handler }) => {
      return (
        <div
          className=""
          data-test-id="delete-resource-generative-ui-container"
        >
          <div className="font-bold text-base mb-2">
            Delete these resources?
          </div>
          <Resources
            resources={resources.filter((resource) =>
              (args.urls || []).includes(resource.url)
            )}
            customWidth={200}
          />
          {status === "executing" && (
            <div className="mt-4 flex justify-start space-x-2">
              <button
                onClick={() => handler("NO")}
                className="px-4 py-2 text-[#6766FC] border border-[#6766FC] rounded text-sm font-bold"
              >
                Cancel
              </button>
              <button
                data-test-id="button-delete"
                onClick={() => handler("YES")}
                className="px-4 py-2 bg-[#6766FC] text-white rounded text-sm font-bold"
              >
                Delete
              </button>
            </div>
          )}
        </div>
      );
    },
  });

  const resources: Resource[] = state.resources || [];
  const setResources = (resources: Resource[]) => {
    setState({ ...state, resources });
  };

  const [newResource, setNewResource] = useState<Resource>({
    url: "",
    title: "",
    description: "",
  });
  const [isAddResourceOpen, setIsAddResourceOpen] = useState(false);

  const addResource = () => {
    if (newResource.url) {
      setResources([...resources, { ...newResource }]);
      setNewResource({ url: "", title: "", description: "" });
      setIsAddResourceOpen(false);
    }
  };

  const removeResource = (url: string) => {
    setResources(
      resources.filter((resource: Resource) => resource.url !== url)
    );
  };

  const [editResource, setEditResource] = useState<Resource | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [isEditResourceOpen, setIsEditResourceOpen] = useState(false);

  const handleCardClick = (resource: Resource) => {
    setEditResource({ ...resource });
    setOriginalUrl(resource.url);
    setIsEditResourceOpen(true);
  };

  const updateResource = () => {
    if (editResource && originalUrl) {
      setResources(
        resources.map((resource) =>
          resource.url === originalUrl ? { ...editResource } : resource
        )
      );
      setEditResource(null);
      setOriginalUrl(null);
      setIsEditResourceOpen(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col overflow-hidden bg-[#F5F8FF]">
      <div className="flex-1 min-h-0 overflow-y-auto p-10 space-y-8 pb-10">
        {/* Research Question display */}
        {state.research_question && (
          <div className="p-4 bg-[#6766FC]/10 rounded-xl border border-[#6766FC]/20">
            <div className="text-xs font-medium text-[#6766FC] mb-1">Current Research Question</div>
            <div className="text-sm text-gray-800">{state.research_question}</div>
          </div>
        )}

        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-medium text-primary">Resources</h2>
            <EditResourceDialog
              isOpen={isEditResourceOpen}
              onOpenChange={setIsEditResourceOpen}
              editResource={editResource}
              setEditResource={setEditResource}
              updateResource={updateResource}
            />
            <AddResourceDialog
              isOpen={isAddResourceOpen}
              onOpenChange={setIsAddResourceOpen}
              newResource={newResource}
              setNewResource={setNewResource}
              addResource={addResource}
            />
          </div>
          {resources.length === 0 && (
            <div className="text-sm text-slate-400">
              Click the button above to add resources.
            </div>
          )}

          {resources.length !== 0 && (
            <Resources
              resources={resources}
              handleCardClick={handleCardClick}
              removeResource={removeResource}
            />
          )}
        </div>

        <ResearchDraft 
          report={state.report || ""} 
          onReportChange={(report) => setState({ ...state, report })} 
        />
      </div>
    </div>
  );
}

/**
 * Research Draft component with Markdown preview toggle
 */
function ResearchDraft({ 
  report, 
  onReportChange 
}: { 
  report: string; 
  onReportChange: (report: string) => void;
}) {
  const [isPreview, setIsPreview] = useState(true);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-medium text-primary">Research Draft</h2>
        <div className="flex items-center gap-1 bg-white rounded-lg p-1 shadow-sm">
          <button
            onClick={() => setIsPreview(false)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
              !isPreview 
                ? "bg-[#6766FC] text-white" 
                : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <Pencil className="w-3.5 h-3.5" />
            Edit
          </button>
          <button
            onClick={() => setIsPreview(true)}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
              isPreview 
                ? "bg-[#6766FC] text-white" 
                : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <Eye className="w-3.5 h-3.5" />
            Preview
          </button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden">
        {isPreview ? (
          <div 
            className="h-full overflow-y-auto bg-white rounded-xl px-6 py-8 prose prose-sm max-w-none
              prose-headings:text-gray-900 prose-p:text-gray-700 prose-a:text-[#6766FC]
              prose-strong:text-gray-900 prose-code:bg-gray-100 prose-code:px-1 prose-code:rounded
              prose-pre:bg-gray-900 prose-pre:text-gray-100
              prose-ul:list-disc prose-ol:list-decimal
              prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-th:bg-gray-50 prose-th:p-2
              prose-td:border prose-td:border-gray-300 prose-td:p-2"
          >
            {report ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {report}
              </ReactMarkdown>
            ) : (
              <p className="text-slate-400 italic">No research draft yet...</p>
            )}
          </div>
        ) : (
          <Textarea
            data-test-id="research-draft"
            placeholder="Write your research draft here (supports Markdown)"
            value={report}
            onChange={(e) => onReportChange(e.target.value)}
            aria-label="Research draft"
            className="h-full bg-white px-6 py-8 border-0 shadow-none rounded-xl text-md font-mono 
              focus-visible:ring-0 placeholder:text-slate-400 resize-none"
          />
        )}
      </div>
    </div>
  );
}
