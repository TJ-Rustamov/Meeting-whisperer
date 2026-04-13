import { useState, useCallback, useEffect } from "react";
import { AppSidebar } from "@/components/AppSidebar";
import { MeetingRecorder } from "@/components/MeetingRecorder";
import { MeetingsList } from "@/components/MeetingsList";
import { MeetingDetail } from "@/components/MeetingDetail";
import { SettingsPanel } from "@/components/SettingsPanel";
import {
  getMeeting,
  getMeetings,
  Meeting,
} from "@/lib/meetingStore";
import { toast } from "sonner";

const Index = () => {
  const [activeTab, setActiveTab] = useState<"meeting" | "meetings" | "settings">("meeting");
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string | null>(null);
  const [isRecorderActive, setIsRecorderActive] = useState(false);

  const refreshMeetings = useCallback(() => {
    getMeetings()
      .then(setMeetings)
      .catch((error) => {
        console.error(error);
        toast.error("Failed to load meetings");
      });
  }, []);

  useEffect(() => {
    refreshMeetings();
  }, [refreshMeetings]);

  const handleMeetingStop = useCallback(
    (meetingId: string) => {
      refreshMeetings();
      setSelectedMeetingId(meetingId);
      setActiveTab("meetings");
    },
    [refreshMeetings]
  );

  const selectedMeeting = meetings.find((m) => m.id === selectedMeetingId);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setSelectedMeetingId(null);
        }}
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        {activeTab !== "meeting" && isRecorderActive && (
          <div className="border-b border-border bg-card/90 px-4 py-2 text-sm text-foreground">
            Recording in progress. Live transcript is still running in the Meeting tab.
          </div>
        )}

        <div className={activeTab === "meeting" ? "flex-1 min-h-0" : "hidden"} aria-hidden={activeTab !== "meeting"}>
          <MeetingRecorder
            onStop={handleMeetingStop}
            onRecordingStateChange={setIsRecorderActive}
          />
        </div>

        {activeTab === "meetings" && !selectedMeeting && (
          <MeetingsList
            meetings={meetings}
            onSelect={(id) => setSelectedMeetingId(id)}
            onRefresh={refreshMeetings}
          />
        )}

        {activeTab === "meetings" && selectedMeeting && (
          <MeetingDetail
            meeting={selectedMeeting}
            onBack={() => setSelectedMeetingId(null)}
            onUpdate={async () => {
              if (!selectedMeetingId) return;
              const updated = await getMeeting(selectedMeetingId);
              setMeetings((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
            }}
          />
        )}

        {activeTab === "settings" && <SettingsPanel />}
      </main>
    </div>
  );
};

export default Index;
