import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Loader2, Search, MessageSquare, CheckCircle2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";

interface ProcessingState {
  investigation_id: string;
}

interface StatusResponse {
  investigation_id: string;
  status: "processing" | "searching" | "contacting" | "completed";
  progress: number;
  message: string;
  suppliers?: any[];
}

const Processing = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const processingState = location.state as ProcessingState;
  
  const [status, setStatus] = useState<StatusResponse>({
    investigation_id: processingState?.investigation_id || "",
    status: "processing",
    progress: 0,
    message: "Initializing AI agents...",
  });
  const [errorCount, setErrorCount] = useState(0);
  const maxErrors = 3;

  useEffect(() => {
    if (!processingState?.investigation_id) {
      console.warn("⚠️ No investigation ID found, redirecting to home");
      toast.error("Missing investigation ID");
      navigate("/");
      return;
    }

    console.log("🔍 Starting status polling for investigation:", processingState.investigation_id);

    let pollCount = 0;
    const maxPolls = 30; // Increased to 90 seconds (30 * 3s)

    const pollStatus = async () => {
      try {
        console.log(`📡 Polling status (attempt ${pollCount + 1}/${maxPolls})...`);
        
        const response = await fetch(
          `http://localhost:8000/api/v1/investigations/${processingState.investigation_id}/status`
        );

        console.log("📡 Status response:", response.status, response.statusText);

        if (!response.ok) {
          const errorText = await response.text();
          console.error("❌ Status fetch failed:", errorText);
          throw new Error(`Status fetch failed: ${response.status}`);
        }

        const data: StatusResponse = await response.json();
        console.log("✅ Status data:", data);
        
        setStatus(data);
        setErrorCount(0); // Reset error count on success

        if (data.status === "completed" && data.suppliers) {
          console.log(`✅ Investigation completed with ${data.suppliers.length} suppliers`);
          toast.success(`Found ${data.suppliers.length} matching suppliers!`);
          
          // Navigate to results with supplier data
          setTimeout(() => {
            navigate("/results", {
              state: {
                investigation_id: data.investigation_id,
                cached: false,
                suppliers: data.suppliers,
                timestamp: new Date().toISOString(),
              },
            });
          }, 1000);
        }
      } catch (error) {
        console.error("❌ Error polling status:", error);
        setErrorCount(prev => prev + 1);
        
        if (errorCount + 1 >= maxErrors) {
          console.error("❌ Max errors reached, stopping poll");
          toast.error("Connection to backend lost. Please check if the backend is running.");
          setTimeout(() => navigate("/"), 3000);
        }
      }
    };

    // Poll every 3 seconds
    const interval = setInterval(() => {
      pollCount++;
      pollStatus();

      if (pollCount >= maxPolls) {
        console.warn("⚠️ Max polls reached, stopping");
        clearInterval(interval);
        toast.warning("Investigation is taking longer than expected. Please check back later.");
      }
    }, 3000);

    // Initial poll
    pollStatus();

    return () => {
      console.log("🧹 Cleaning up status polling");
      clearInterval(interval);
    };
  }, [processingState, navigate, errorCount]);

  const getStatusIcon = () => {
    switch (status.status) {
      case "processing":
        return <Loader2 className="h-8 w-8 animate-spin text-primary" />;
      case "searching":
        return <Search className="h-8 w-8 animate-pulse text-primary" />;
      case "contacting":
        return <MessageSquare className="h-8 w-8 animate-pulse text-primary" />;
      case "completed":
        return <CheckCircle2 className="h-8 w-8 text-primary" />;
      default:
        return <Loader2 className="h-8 w-8 animate-spin text-primary" />;
    }
  };

  const getStatusTitle = () => {
    switch (status.status) {
      case "processing":
        return "Analyzing Your Requirements";
      case "searching":
        return "Searching Global Supplier Database";
      case "contacting":
        return "AI Agents Contacting Suppliers";
      case "completed":
        return "Matches Found!";
      default:
        return "Processing";
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-6 py-12 md:py-20">
        {/* Header */}
        <header className="mb-12 text-center">
          <h1 className="mb-4 text-4xl font-bold tracking-tight text-foreground md:text-5xl">
            Finding Your Perfect Suppliers
          </h1>
          <p className="mx-auto max-w-2xl text-lg text-muted-foreground">
            Our AI agents are working hard to find and contact the best suppliers for your needs
          </p>
        </header>

        {/* Processing Card */}
        <div className="rounded-2xl border border-border bg-card p-8 shadow-sm md:p-12">
          <div className="space-y-8">
            {/* Investigation ID */}
            <div className="text-center">
              <p className="text-sm text-muted-foreground">Investigation ID</p>
              <p className="mt-1 font-mono text-lg font-medium text-foreground">
                {status.investigation_id}
              </p>
            </div>

            {/* Status Icon */}
            <div className="flex justify-center">{getStatusIcon()}</div>

            {/* Status Title */}
            <div className="text-center">
              <h2 className="text-2xl font-semibold text-foreground">
                {getStatusTitle()}
              </h2>
              <p className="mt-2 text-muted-foreground">{status.message}</p>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <Progress value={status.progress} className="h-2" />
              <p className="text-center text-sm text-muted-foreground">
                {status.progress}% Complete
              </p>
            </div>

            {/* Status Steps */}
            <div className="grid gap-4 md:grid-cols-3">
              <div
                className={`rounded-lg border p-4 text-center transition-all ${
                  status.status === "processing"
                    ? "border-primary bg-primary/5"
                    : status.progress > 25
                    ? "border-primary/50 bg-primary/10"
                    : "border-border"
                }`}
              >
                <Loader2 className="mx-auto mb-2 h-6 w-6" />
                <p className="text-sm font-medium">Processing</p>
              </div>

              <div
                className={`rounded-lg border p-4 text-center transition-all ${
                  status.status === "searching"
                    ? "border-primary bg-primary/5"
                    : status.progress > 50
                    ? "border-primary/50 bg-primary/10"
                    : "border-border"
                }`}
              >
                <Search className="mx-auto mb-2 h-6 w-6" />
                <p className="text-sm font-medium">Searching</p>
              </div>

              <div
                className={`rounded-lg border p-4 text-center transition-all ${
                  status.status === "contacting" || status.status === "completed"
                    ? "border-primary bg-primary/5"
                    : "border-border"
                }`}
              >
                <MessageSquare className="mx-auto mb-2 h-6 w-6" />
                <p className="text-sm font-medium">Contacting</p>
              </div>
            </div>

            {/* Additional Info */}
            <div className="rounded-lg bg-muted p-4 text-center text-sm text-muted-foreground">
              This typically takes 30-60 seconds. We're analyzing thousands of suppliers
              and initiating first contact with the best matches.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Processing;
