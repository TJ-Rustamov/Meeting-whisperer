import { useState, useEffect } from "react";
import { AppSettings, getSettings, saveSettings, shutdownApp } from "@/lib/meetingStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { User } from "lucide-react";

export function SettingsPanel() {
  const [settings, setSettings] = useState<AppSettings>({
    llmProvider: "gemini",
    llmApiKey: "",
    profile: { name: "", email: "", avatarUrl: "" },
  });
  const [password, setPassword] = useState("");

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch((error) => {
        console.error(error);
        toast.error("Failed to load settings");
      });
  }, []);

  const handleSave = async () => {
    try {
      await saveSettings(settings);
      toast.success("Settings saved");
    } catch (error) {
      console.error(error);
      toast.error("Failed to save settings");
    }
  };

  const handleExitApp = async () => {
    if (!window.confirm("Exit Meeting Whisperer now?")) return;
    try {
      await shutdownApp();
      toast.success("Shutting down application...");
    } catch (error) {
      console.error(error);
      toast.error("Failed to shut down app");
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6">
      <h2 className="text-xl font-semibold text-foreground mb-6">Settings</h2>

      {/* Profile */}
      <div className="space-y-6">
        <div className="bg-card border border-border rounded-xl p-5 space-y-4">
          <h3 className="font-medium text-foreground">Profile</h3>

          <div className="flex items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-accent flex items-center justify-center">
              {settings.profile.avatarUrl ? (
                <img
                  src={settings.profile.avatarUrl}
                  alt="Avatar"
                  className="h-16 w-16 rounded-full object-cover"
                />
              ) : (
                <User className="h-8 w-8 text-muted-foreground" />
              )}
            </div>
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground">Avatar URL</Label>
              <Input
                value={settings.profile.avatarUrl}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    profile: { ...settings.profile, avatarUrl: e.target.value },
                  })
                }
                placeholder="https://example.com/avatar.png"
                className="mt-1"
              />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <Label className="text-xs text-muted-foreground">Name</Label>
              <Input
                value={settings.profile.name}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    profile: { ...settings.profile, name: e.target.value },
                  })
                }
                placeholder="Your name"
                className="mt-1"
              />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Email</Label>
              <Input
                value={settings.profile.email}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    profile: { ...settings.profile, email: e.target.value },
                  })
                }
                placeholder="you@email.com"
                className="mt-1"
              />
            </div>
          </div>

          <div>
            <Label className="text-xs text-muted-foreground">Password</Label>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Change password"
              className="mt-1"
            />
          </div>
        </div>

        {/* LLM Settings */}
        <div className="bg-card border border-border rounded-xl p-5 space-y-4">
          <h3 className="font-medium text-foreground">LLM Configuration</h3>
          <p className="text-sm text-muted-foreground">
            Add your API key to enable meeting summarization
          </p>

          <div>
            <Label className="text-xs text-muted-foreground">Provider</Label>
            <Select
              value={settings.llmProvider}
              onValueChange={(v: "openai" | "gemini") =>
                setSettings({ ...settings, llmProvider: v })
              }
            >
              <SelectTrigger className="mt-1">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="openai">OpenAI</SelectItem>
                <SelectItem value="gemini">Google Gemini</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs text-muted-foreground">API Key</Label>
            <Input
              type="password"
              value={settings.llmApiKey}
              onChange={(e) =>
                setSettings({ ...settings, llmApiKey: e.target.value })
              }
              placeholder={
                settings.llmProvider === "openai"
                  ? "sk-..."
                  : "AIza..."
              }
              className="mt-1"
            />
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Button onClick={handleSave} className="w-full">
            Save Settings
          </Button>
          <Button variant="destructive" onClick={handleExitApp} className="w-full">
            Exit Program
          </Button>
        </div>
      </div>
    </div>
  );
}
