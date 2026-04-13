import { Mic, List, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

interface AppSidebarProps {
  activeTab: "meeting" | "meetings" | "settings";
  onTabChange: (tab: "meeting" | "meetings" | "settings") => void;
}

const tabs = [
  { id: "meeting" as const, label: "Meeting", icon: Mic },
  { id: "meetings" as const, label: "All Meetings", icon: List },
  { id: "settings" as const, label: "Settings", icon: Settings },
];

export function AppSidebar({ activeTab, onTabChange }: AppSidebarProps) {
  return (
    <nav className="w-16 md:w-56 border-r border-border bg-card flex flex-col shrink-0">
      <div className="p-4 md:p-6">
        <h1 className="hidden md:block text-xl font-bold text-primary">
          MeetScribe
        </h1>
        <div className="md:hidden flex justify-center">
          <Mic className="h-6 w-6 text-primary" />
        </div>
      </div>
      <div className="flex flex-col gap-1 px-2 md:px-3">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            <tab.icon className="h-5 w-5 shrink-0" />
            <span className="hidden md:inline">{tab.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
}
