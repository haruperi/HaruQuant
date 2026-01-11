"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { getDocContent, saveDocContent } from "@/lib/api/docs"
import { Loader2, Save, X } from "lucide-react"
import { toast } from "sonner"

interface DocEditorProps {
  path: string
  onClose: () => void
  onSave?: () => void
}

export function DocEditor({ path, onClose, onSave }: DocEditorProps) {
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const loadContent = async () => {
      try {
        const data = await getDocContent(path)
        setContent(data.content)
      } catch (error) {
        toast.error("Failed to load content")
        console.error(error)
      } finally {
        setLoading(false)
      }
    }
    loadContent()
  }, [path])

  const handleSave = async () => {
    setSaving(true)
    try {
      await saveDocContent(path, content)
      toast.success("Document saved successfully")
      if (onSave) onSave()
      onClose()
    } catch (error) {
      toast.error("Failed to save document")
      console.error(error)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4 h-full">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Editing: {path}</h3>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={saving}>
            <X className="mr-2 h-4 w-4" />
            Cancel
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save
          </Button>
        </div>
      </div>
      <Textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="flex-1 font-mono min-h-[500px]"
      />
    </div>
  )
}
