"use client"

import { useEffect, useState } from "react"
import { getDocsFiles, deleteDoc, saveDocContent, FileNode } from "@/lib/api/docs"
import { Button } from "@/components/ui/button"
import { Plus, Trash2, FileText, Folder, RefreshCw } from "lucide-react"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"

export default function DocumentationManager() {
  const [files, setFiles] = useState<FileNode[]>([])
  const [loading, setLoading] = useState(true)
  const [newFilePath, setNewFilePath] = useState("")
  const [isDialogOpen, setIsDialogOpen] = useState(false)

  const fetchFiles = async () => {
    setLoading(true)
    try {
      const data = await getDocsFiles()
      setFiles(data)
    } catch (error) {
      toast.error("Failed to load files")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchFiles()
  }, [])

  const handleDelete = async (path: string) => {
    if (!confirm(`Are you sure you want to delete ${path}?`)) return
    try {
      await deleteDoc(path)
      toast.success("File deleted")
      fetchFiles()
    } catch (error) {
      toast.error("Failed to delete file")
    }
  }

  const handleCreate = async () => {
    if (!newFilePath) return
    // Ensure .md extension
    const path = newFilePath.endsWith(".md") ? newFilePath : `${newFilePath}.md`
    try {
      await saveDocContent(path, "# New Document\n\nStart writing...")
      toast.success("File created")
      setIsDialogOpen(false)
      setNewFilePath("")
      fetchFiles()
    } catch (error) {
      toast.error("Failed to create file")
    }
  }

  const renderTree = (nodes: FileNode[], level = 0) => {
    return (
      <div className="space-y-1">
        {nodes.map((node) => (
          <div key={node.path} style={{ paddingLeft: `${level * 20}px` }} className="flex items-center justify-between p-2 hover:bg-accent rounded-md group">
             <div className="flex items-center gap-2">
                {node.type === 'directory' ? <Folder className="h-4 w-4 text-primary" /> : <FileText className="h-4 w-4 text-muted-foreground" />}
                <span className="text-sm">{node.name}</span>
             </div>
             {node.type === 'file' && (
                 <Button variant="ghost" size="icon" className="h-6 w-6 opacity-0 group-hover:opacity-100" onClick={() => handleDelete(node.path)}>
                     <Trash2 className="h-3 w-3 text-destructive" />
                 </Button>
             )}
             {node.children && renderTree(node.children, level + 1)}
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="flex-1 p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold tracking-tight">Documentation Manager</h2>
         <div className="flex gap-2">
            <Button variant="outline" size="icon" onClick={fetchFiles}><RefreshCw className="h-4 w-4" /></Button>
            <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
              <DialogTrigger asChild>
                <Button><Plus className="mr-2 h-4 w-4" /> New File</Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Create New Document</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">File Path (relative to docs/)</label>
                    <Input
                      placeholder="fundamentals/new-guide"
                      value={newFilePath}
                      onChange={(e) => setNewFilePath(e.target.value)}
                    />
                    <p className="text-xs text-muted-foreground">Example: fundamentals/my-new-guide</p>
                  </div>
                  <Button onClick={handleCreate} disabled={!newFilePath}>Create</Button>
                </div>
              </DialogContent>
            </Dialog>
         </div>
      </div>

      <div className="border rounded-lg p-4 min-h-[400px]">
        {loading ? <div>Loading...</div> : renderTree(files)}
      </div>
    </div>
  )
}
