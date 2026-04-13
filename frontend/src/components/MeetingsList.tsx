import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { Meeting, formatTime, deleteMeeting, renameMeeting } from "@/lib/meetingStore";
import { Trash2, ChevronRight, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

interface MeetingsListProps {
  meetings: Meeting[];
  onSelect: (id: string) => void;
  onRefresh: () => void;
}

export function MeetingsList({ meetings, onSelect, onRefresh }: MeetingsListProps) {
  const [pendingDelete, setPendingDelete] = useState<Meeting | null>(null);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const [renameTarget, setRenameTarget] = useState<Meeting | null>(null);
  const [renameTitle, setRenameTitle] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setSelectedIds((prev) => {
      const available = new Set(meetings.map((meeting) => meeting.id));
      const next = new Set<string>();
      for (const id of prev) {
        if (available.has(id)) {
          next.add(id);
        }
      }
      return next;
    });
  }, [meetings]);

  const selectedCount = selectedIds.size;
  const allSelected = meetings.length > 0 && selectedCount === meetings.length;
  const someSelected = selectedCount > 0 && !allSelected;

  const selectedMeetingsLabel = useMemo(() => {
    if (selectedCount === 1) return "1 meeting selected";
    return `${selectedCount} meetings selected`;
  }, [selectedCount]);

  const requestDelete = (e: MouseEvent, meeting: Meeting) => {
    e.stopPropagation();
    setPendingDelete(meeting);
  };

  const toggleMeetingSelection = (meetingId: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(meetingId);
      } else {
        next.delete(meetingId);
      }
      return next;
    });
  };

  const toggleSelectAll = (checked: boolean) => {
    if (!checked) {
      setSelectedIds(new Set());
      return;
    }
    setSelectedIds(new Set(meetings.map((meeting) => meeting.id)));
  };

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    try {
      setIsDeleting(true);
      await deleteMeeting(pendingDelete.id);
      onRefresh();
      toast.success("Meeting deleted");
      setPendingDelete(null);
    } catch (error) {
      console.error(error);
      toast.error("Failed to delete meeting");
    } finally {
      setIsDeleting(false);
    }
  };

  const confirmBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    const ids = Array.from(selectedIds);

    try {
      setIsDeleting(true);
      const results = await Promise.allSettled(ids.map((id) => deleteMeeting(id)));

      const failedIds = new Set<string>();
      let successCount = 0;
      results.forEach((result, index) => {
        if (result.status === "fulfilled") {
          successCount += 1;
        } else {
          failedIds.add(ids[index]);
        }
      });

      onRefresh();

      if (successCount > 0) {
        toast.success(
          successCount === 1 ? "1 meeting deleted" : `${successCount} meetings deleted`
        );
      }
      if (failedIds.size > 0) {
        toast.error(
          failedIds.size === 1
            ? "1 meeting failed to delete"
            : `${failedIds.size} meetings failed to delete`
        );
      }

      setSelectedIds(failedIds);
      setBulkDeleteOpen(false);
    } catch (error) {
      console.error(error);
      toast.error("Bulk delete failed");
    } finally {
      setIsDeleting(false);
    }
  };

  const openRename = (e: MouseEvent, meeting: Meeting) => {
    e.stopPropagation();
    setRenameTarget(meeting);
    setRenameTitle(meeting.title);
  };

  const confirmRename = async () => {
    if (!renameTarget) return;
    const nextTitle = renameTitle.trim();
    if (!nextTitle) {
      toast.error("Title cannot be empty");
      return;
    }
    try {
      setIsRenaming(true);
      await renameMeeting(renameTarget.id, nextTitle);
      onRefresh();
      toast.success("Meeting renamed");
      setRenameTarget(null);
    } catch (error) {
      console.error(error);
      toast.error("Failed to rename meeting");
    } finally {
      setIsRenaming(false);
    }
  };

  if (meetings.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-lg font-medium text-muted-foreground">No meetings yet</p>
          <p className="text-sm text-muted-foreground">
            Start a recording to create your first meeting
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <h2 className="text-xl font-semibold text-foreground mb-4">All Meetings</h2>
        <div className="mb-4 rounded-xl border border-border bg-card/60 p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={allSelected ? true : someSelected ? "indeterminate" : false}
                onCheckedChange={(checked) => toggleSelectAll(checked === true)}
                aria-label="Select all meetings"
              />
              <span>{selectedMeetingsLabel}</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setSelectedIds(new Set())}
                disabled={selectedCount === 0 || isDeleting}
              >
                Clear
              </Button>
              <Button
                size="sm"
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                onClick={() => setBulkDeleteOpen(true)}
                disabled={selectedCount === 0 || isDeleting}
              >
                Delete selected ({selectedCount})
              </Button>
            </div>
          </div>
        </div>
        <div className="space-y-2">
          {meetings.map((meeting) => (
            <div
              key={meeting.id}
              onClick={() => onSelect(meeting.id)}
              className="flex items-center justify-between p-4 rounded-xl bg-card border border-border hover:border-primary/30 hover:shadow-sm transition-all cursor-pointer group"
            >
              <div className="min-w-0 flex items-center gap-3">
                <Checkbox
                  checked={selectedIds.has(meeting.id)}
                  onCheckedChange={(checked) => toggleMeetingSelection(meeting.id, checked === true)}
                  onClick={(e) => e.stopPropagation()}
                  aria-label={`Select ${meeting.title}`}
                />
                <div className="min-w-0">
                  <h3 className="font-medium text-foreground truncate">{meeting.title}</h3>
                  <div className="flex gap-3 text-xs text-muted-foreground mt-1">
                    <span>{new Date(meeting.date).toLocaleDateString()}</span>
                    <span>{formatTime(meeting.duration)}</span>
                    <span>{meeting.transcript.length} segments</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100"
                  onClick={(e) => openRename(e, meeting)}
                  aria-label="Rename meeting"
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="opacity-0 group-hover:opacity-100 text-destructive hover:text-destructive"
                  onClick={(e) => requestDelete(e, meeting)}
                  aria-label="Delete meeting"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
          ))}
        </div>
      </div>
      <AlertDialog open={pendingDelete !== null} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete meeting?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete "{pendingDelete?.title ?? "this meeting"}" and its transcript.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={isDeleting}
              onClick={confirmDelete}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={bulkDeleteOpen} onOpenChange={setBulkDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete selected meetings?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {selectedCount} selected{" "}
              {selectedCount === 1 ? "meeting" : "meetings"}, including transcripts and media files.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={isDeleting || selectedCount === 0}
              onClick={confirmBulkDelete}
            >
              {isDeleting ? "Deleting..." : `Delete ${selectedCount}`}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={renameTarget !== null} onOpenChange={(open) => !open && setRenameTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename meeting</DialogTitle>
            <DialogDescription>Update the title for this meeting.</DialogDescription>
          </DialogHeader>
          <Input
            value={renameTitle}
            onChange={(e) => setRenameTitle(e.currentTarget.value)}
            placeholder="Meeting title"
            autoFocus
            maxLength={255}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameTarget(null)} disabled={isRenaming}>
              Cancel
            </Button>
            <Button onClick={confirmRename} disabled={isRenaming}>
              {isRenaming ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
