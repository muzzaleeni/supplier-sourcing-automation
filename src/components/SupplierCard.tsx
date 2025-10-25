import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, Mail, Phone, Globe, MapPin, MessageSquare } from "lucide-react";
import { useState } from "react";

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

interface SupplierCardProps {
  supplier: Supplier;
}

export function SupplierCard({ supplier }: SupplierCardProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <CardTitle className="text-xl">{supplier.name}</CardTitle>
            <CardDescription className="mt-2 flex items-center gap-1">
              <MapPin className="h-3.5 w-3.5" />
              {supplier.location}
            </CardDescription>
          </div>
          <Badge variant={supplier.match_score >= 90 ? "default" : "secondary"} className="text-sm font-semibold">
            {supplier.match_score}% Match
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Contact Information */}
        <div className="space-y-2 text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Mail className="h-4 w-4" />
            <a href={`mailto:${supplier.contact_email}`} className="hover:text-foreground transition-colors">
              {supplier.contact_email}
            </a>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Phone className="h-4 w-4" />
            <a href={`tel:${supplier.contact_phone}`} className="hover:text-foreground transition-colors">
              {supplier.contact_phone}
            </a>
          </div>
          <div className="flex items-center gap-2 text-muted-foreground">
            <Globe className="h-4 w-4" />
            <a href={supplier.website} target="_blank" rel="noopener noreferrer" className="hover:text-foreground transition-colors">
              {supplier.website}
            </a>
          </div>
        </div>

        {/* Capabilities */}
        <div className="space-y-2">
          <p className="text-sm font-medium">Capabilities</p>
          <div className="flex flex-wrap gap-2">
            {supplier.capabilities.map((capability, index) => (
              <Badge key={index} variant="outline" className="text-xs">
                {capability}
              </Badge>
            ))}
          </div>
        </div>

        {/* Conversation Log */}
        <Collapsible open={isOpen} onOpenChange={setIsOpen}>
          <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border border-border bg-muted/50 px-4 py-2 text-sm font-medium transition-colors hover:bg-muted">
            <span className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Conversation Log ({supplier.conversation_log.length} messages)
            </span>
            <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? "rotate-180" : ""}`} />
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3">
            <div className="space-y-3 rounded-lg border border-border bg-card p-4">
              {supplier.conversation_log.map((turn, index) => {
                const getRoleDisplay = () => {
                  switch(turn.role) {
                    case "buyer": return { label: "Buyer (You)", color: "text-blue-600" };
                    case "supplier": return { label: "Supplier Response", color: "text-green-600" };
                    case "system": return { label: "AI Analysis", color: "text-amber-600" };
                    default: return { label: turn.role, color: "text-muted-foreground" };
                  }
                };
                const roleInfo = getRoleDisplay();
                
                return (
                  <div key={index} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-semibold ${roleInfo.color}`}>
                        {roleInfo.label}
                      </span>
                      <span className="text-xs text-muted-foreground">{turn.timestamp}</span>
                    </div>
                    <p className="text-sm text-foreground whitespace-pre-wrap">{turn.content}</p>
                    {index < supplier.conversation_log.length - 1 && <div className="mt-3 h-px bg-border" />}
                  </div>
                );
              })}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
