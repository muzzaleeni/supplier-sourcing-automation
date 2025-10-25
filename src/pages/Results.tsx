import { useLocation, useNavigate } from "react-router-dom";
import { SupplierCard } from "@/components/SupplierCard";
import { Button } from "@/components/ui/button";
import { ArrowLeft, CheckCircle2 } from "lucide-react";
import { useEffect } from "react";
import { toast } from "sonner";

interface ConversationTurn {
  role: string;
  content: string;
  timestamp: string;
}

interface Supplier {
  name: string;
  contact_email: string;
  contact_phone: string;
  website: string;
  location: string;
  match_score: number;
  capabilities: string[];
  conversation_log: ConversationTurn[];
}

interface ResultsData {
  investigation_id: string;
  cached: boolean;
  suppliers: Supplier[];
}

const Results = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const resultsData = location.state as ResultsData | null;

  useEffect(() => {
    if (!resultsData) {
      console.warn("⚠️ No results data found, redirecting to home");
      toast.error("No results data found");
      navigate("/");
      return;
    }
    
    console.log("✅ Results page loaded with data:", {
      investigation_id: resultsData.investigation_id,
      suppliers_count: resultsData.suppliers?.length || 0,
      cached: resultsData.cached
    });

    if (!resultsData.suppliers || resultsData.suppliers.length === 0) {
      console.warn("⚠️ No suppliers found in results");
      toast.warning("No suppliers were found matching your requirements");
    }
  }, [resultsData, navigate]);

  if (!resultsData) {
    return null;
  }

  const { investigation_id, cached, suppliers } = resultsData;

  // Handle case where suppliers array is empty
  if (!suppliers || suppliers.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto max-w-6xl px-6 py-12 md:py-20">
          <Button variant="ghost" onClick={() => navigate("/")} className="mb-4 -ml-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Form
          </Button>
          
          <div className="rounded-2xl border border-border bg-card p-12 text-center">
            <h1 className="mb-4 text-2xl font-bold text-foreground">No Suppliers Found</h1>
            <p className="text-muted-foreground">
              We couldn't find any suppliers matching your requirements at this time.
              Please try again with different criteria.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-6xl px-6 py-12 md:py-20">
        {/* Header */}
        <div className="mb-8">
          <Button variant="ghost" onClick={() => navigate("/")} className="mb-4 -ml-4">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Form
          </Button>

          <div className="mb-6 flex items-center gap-3">
            <CheckCircle2 className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
                Suppliers Found
              </h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Investigation ID: {investigation_id}
                {cached && <span className="ml-2 text-xs">(Cached Result)</span>}
              </p>
            </div>
          </div>

          <p className="text-lg text-muted-foreground">
            We've matched you with {suppliers.length} qualified supplier{suppliers.length !== 1 ? "s" : ""} based on your requirements.
          </p>
        </div>

        {/* Supplier Cards Grid */}
        <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
          {suppliers.map((supplier, index) => (
            <SupplierCard key={index} supplier={supplier} />
          ))}
        </div>

        {/* Footer */}
        <div className="mt-12 rounded-2xl border border-border bg-card p-6 text-center">
          <p className="text-sm text-muted-foreground">
            Our team will review these matches and reach out to coordinate next steps within 24-48 hours.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Results;
