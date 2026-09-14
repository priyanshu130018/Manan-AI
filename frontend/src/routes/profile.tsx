import { useState, useEffect } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import {
  User as UserIcon,
  Mail,
  Phone,
  Shield,
  Key,
  Brain,
  Trash2,
  Loader2,
  LogOut,
  Save,
  CheckCircle2,
  AlertTriangle,
  Eye,
  EyeOff,
  Plus,
  Pencil,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useAuth } from "@/hooks/use-auth";
import { updateProfile, changePassword } from "@/services/auth";
import { listMemories, createMemory, updateMemory, deleteMemory, clearAllMemories, type MemoryItem } from "@/services/memory";
import { readSettings, writeSettings } from "@/services/axios";

export const Route = createFileRoute("/profile")({
  component: ProfilePage,
});

function ProfilePage() {
  const navigate = useNavigate();
  const { user, logout, refreshUser } = useAuth();

  // Profile fields
  const [name, setName] = useState(user?.name || "");
  const [mobile, setMobile] = useState(user?.mobile || "");
  const [savingProfile, setSavingProfile] = useState(false);

  // Password fields
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirmNew, setShowConfirmNew] = useState(false);
  const [changingPassword, setChangingPassword] = useState(false);

  // Memory fields
  const [appSettings, setAppSettings] = useState(readSettings);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loadingMemories, setLoadingMemories] = useState(false);
  const [deletingMemoryId, setDeletingMemoryId] = useState<string | null>(null);
  const [isAddMemoryOpen, setIsAddMemoryOpen] = useState(false);
  const [newMemoryContent, setNewMemoryContent] = useState("");
  const [savingNewMemory, setSavingNewMemory] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);
  const [editMemoryContent, setEditMemoryContent] = useState("");
  const [savingEditMemory, setSavingEditMemory] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name);
      setMobile(user.mobile || "");
    }
  }, [user]);

  const loadMemories = async () => {
    setLoadingMemories(true);
    try {
      const data = await listMemories();
      setMemories(data);
    } catch {
      setMemories([]);
    } finally {
      setLoadingMemories(false);
    }
  };

  useEffect(() => {
    loadMemories();
  }, []);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast.error("Name cannot be empty.");
      return;
    }
    setSavingProfile(true);
    try {
      await updateProfile({ name: name.trim(), mobile: mobile.trim() || undefined });
      await refreshUser();
      toast.success("Profile updated successfully!");
    } catch (err: any) {
      toast.error(err?.friendlyMessage || "Failed to update profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentPassword) {
      toast.error("Please enter your current password.");
      return;
    }
    if (!newPassword || newPassword.length < 6) {
      toast.error("New password must be at least 6 characters.");
      return;
    }
    if (newPassword !== confirmNewPassword) {
      toast.error("New passwords do not match.");
      return;
    }
    setChangingPassword(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      toast.success("Password changed successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
    } catch (err: any) {
      toast.error(err?.friendlyMessage || "Failed to change password.");
    } finally {
      setChangingPassword(false);
    }
  };

  const handleToggleMemory = (enabled: boolean) => {
    const updated = { ...appSettings, memoryEnabled: enabled };
    setAppSettings(updated);
    writeSettings(updated);
    toast.success(enabled ? "Long-term memory enabled." : "Long-term memory disabled.");
  };

  const handleDeleteMemory = async (id: string) => {
    setDeletingMemoryId(id);
    try {
      await deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
      toast.success("Memory deleted.");
    } catch {
      toast.error("Could not delete memory.");
    } finally {
      setDeletingMemoryId(null);
    }
  };

  const handleClearAllMemories = async () => {
    try {
      await clearAllMemories();
      setMemories([]);
      toast.success("All memories cleared.");
    } catch {
      toast.error("Could not clear memories.");
    }
  };

  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemoryContent.trim()) return;
    setSavingNewMemory(true);
    try {
      const created = await createMemory(newMemoryContent.trim());
      setMemories((prev) => [created, ...prev]);
      setNewMemoryContent("");
      setIsAddMemoryOpen(false);
      toast.success("Memory added successfully.");
    } catch {
      toast.error("Failed to add memory.");
    } finally {
      setSavingNewMemory(false);
    }
  };

  const handleUpdateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMemory || !editMemoryContent.trim()) return;
    setSavingEditMemory(true);
    try {
      const updated = await updateMemory(editingMemory.id, editMemoryContent.trim());
      setMemories((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
      setEditingMemory(null);
      setEditMemoryContent("");
      toast.success("Memory updated successfully.");
    } catch {
      toast.error("Failed to update memory.");
    } finally {
      setSavingEditMemory(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      toast.success("Logged out.");
      navigate({ to: "/login" });
    } catch {
      toast.error("Could not log out.");
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-background p-4 md:p-8">
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border/60 pb-5">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">User Profile</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Manage your personal information, security credentials, and AI memory
            </p>
          </div>
          <Button variant="destructive" onClick={handleLogout} className="flex items-center gap-2 self-start sm:self-auto">
            <LogOut className="h-4 w-4" />
            Log Out
          </Button>
        </div>

        {/* Profile Details Card */}
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <UserIcon className="h-5 w-5 text-primary" />
              Personal Information
            </CardTitle>
            <CardDescription>Update your contact and identification details</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSaveProfile} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor="prof-name">Full Name</Label>
                  <Input
                    id="prof-name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="prof-email">Email Address</Label>
                  <div className="relative">
                    <Input
                      id="prof-email"
                      value={user?.email || ""}
                      disabled
                      className="bg-muted text-muted-foreground pr-8"
                    />
                    <Mail className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="prof-mobile">Mobile Number</Label>
                  <div className="relative">
                    <Input
                      id="prof-mobile"
                      value={mobile}
                      onChange={(e) => setMobile(e.target.value)}
                      placeholder="+1 234 567 8900"
                    />
                    <Phone className="absolute right-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Authentication Provider</Label>
                  <div className="flex h-9 items-center gap-2 rounded-md border border-input bg-muted px-3 text-sm text-muted-foreground">
                    <Shield className="h-4 w-4 text-primary" />
                    <span className="capitalize">{user?.auth_provider || "Local"}</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <Button type="submit" disabled={savingProfile} className="flex items-center gap-2">
                  {savingProfile ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  Save Changes
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Change Password Card */}
        <Card className="border-border/60 shadow-sm">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Key className="h-5 w-5 text-primary" />
                Change Password
              </CardTitle>
              <CardDescription>Ensure your account remains secure with a strong password</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleChangePassword} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-1.5">
                    <Label htmlFor="curr-pass">Current Password</Label>
                    <div className="relative">
                      <Input
                        id="curr-pass"
                        type={showCurrent ? "text" : "password"}
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowCurrent(!showCurrent)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showCurrent ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="new-pass">New Password</Label>
                    <div className="relative">
                      <Input
                        id="new-pass"
                        type={showNew ? "text" : "password"}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowNew(!showNew)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label htmlFor="conf-pass">Confirm New Password</Label>
                    <div className="relative">
                      <Input
                        id="conf-pass"
                        type={showConfirmNew ? "text" : "password"}
                        value={confirmNewPassword}
                        onChange={(e) => setConfirmNewPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        className="pr-10"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmNew(!showConfirmNew)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      >
                        {showConfirmNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <Button type="submit" variant="secondary" disabled={changingPassword} className="flex items-center gap-2">
                    {changingPassword && <Loader2 className="h-4 w-4 animate-spin" />}
                    Update Password
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

        {/* Long-Term Memory Section */}
        <Card className="border-border/60 shadow-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Brain className="h-5 w-5 text-primary" />
                  Long-Term AI Memory
                </CardTitle>
                <CardDescription>
                  Manan AI remembers personal facts and learning preferences across conversations
                </CardDescription>
              </div>
              <Switch
                checked={appSettings.memoryEnabled}
                onCheckedChange={handleToggleMemory}
                aria-label="Toggle Long-Term Memory"
              />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between border-t border-border/40 pt-4">
              <span className="text-sm font-medium text-foreground">
                Saved Memories ({memories.length})
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsAddMemoryOpen(true)}
                  className="flex items-center gap-1.5"
                >
                  <Plus className="h-4 w-4" />
                  Add Memory
                </Button>
                {memories.length > 0 && (
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="outline" size="sm" className="text-destructive hover:bg-destructive/10">
                        Clear All
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle className="flex items-center gap-2">
                          <AlertTriangle className="h-5 w-5 text-destructive" />
                          Clear all AI memories?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          This will permanently delete all facts and preferences remembered about you. This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={handleClearAllMemories} className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                          Clear All
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </div>
            </div>

            {loadingMemories ? (
              <div className="flex items-center justify-center py-6 text-muted-foreground gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Loading memories...</span>
              </div>
            ) : memories.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border/70 p-6 text-center text-sm text-muted-foreground">
                No memories saved yet. When you chat with Manan AI, explicit facts and preferences you share will automatically appear here.
              </div>
            ) : (
              <div className="space-y-2">
                {memories.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center justify-between rounded-lg border border-border/60 bg-card/60 p-3 text-sm transition-colors hover:bg-muted/40"
                  >
                    <div className="flex items-start gap-2.5 min-w-0 pr-3">
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500 mt-0.5" />
                      <span className="truncate text-foreground">{m.content}</span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-muted-foreground hover:text-foreground"
                        onClick={() => {
                          setEditingMemory(m);
                          setEditMemoryContent(m.content);
                        }}
                        aria-label="Edit memory"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        disabled={deletingMemoryId === m.id}
                        onClick={() => handleDeleteMemory(m.id)}
                        aria-label="Delete memory"
                      >
                        {deletingMemoryId === m.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Add Memory Dialog */}
            <Dialog open={isAddMemoryOpen} onOpenChange={setIsAddMemoryOpen}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add New AI Memory</DialogTitle>
                  <DialogDescription>
                    Add a personal fact, preference, or context that Manan AI should remember for you.
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleCreateMemory} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="new-memory-input">Memory content</Label>
                    <Input
                      id="new-memory-input"
                      value={newMemoryContent}
                      onChange={(e) => setNewMemoryContent(e.target.value)}
                      placeholder="e.g. I prefer Python for backend and TypeScript for frontend."
                      required
                    />
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setIsAddMemoryOpen(false)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={savingNewMemory || !newMemoryContent.trim()}>
                      {savingNewMemory && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                      Save Memory
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>

            {/* Edit Memory Dialog */}
            <Dialog open={!!editingMemory} onOpenChange={(open) => !open && setEditingMemory(null)}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Edit AI Memory</DialogTitle>
                  <DialogDescription>
                    Update this saved fact or preference.
                  </DialogDescription>
                </DialogHeader>
                <form onSubmit={handleUpdateMemory} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="edit-memory-input">Memory content</Label>
                    <Input
                      id="edit-memory-input"
                      value={editMemoryContent}
                      onChange={(e) => setEditMemoryContent(e.target.value)}
                      placeholder="Updated memory statement"
                      required
                    />
                  </div>
                  <DialogFooter>
                    <Button type="button" variant="outline" onClick={() => setEditingMemory(null)}>
                      Cancel
                    </Button>
                    <Button type="submit" disabled={savingEditMemory || !editMemoryContent.trim()}>
                      {savingEditMemory && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                      Save Changes
                    </Button>
                  </DialogFooter>
                </form>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
