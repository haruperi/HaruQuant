"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Input } from "@/components/ui/input"
import { Checkbox } from "@/components/ui/checkbox"
import { Button } from "@/components/ui/button"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { useState, useEffect } from "react"
import { Plus, Trash2, MessageSquare, Save, X, Eye, EyeOff, Loader2, Copy } from "lucide-react"
import { toast } from "sonner"
import { useSettings } from "@/lib/use-settings"

interface NotificationChannel {
  id: string
  name: string
  type: "telegram" | "discord" | "email"
  enabled: boolean
  config: {
    botToken?: string
    chatIds?: string
    soundOn?: boolean
    protectContent?: boolean
    webhookUrl?: string
    emailAddress?: string
  }
}

interface AlertTriggers {
  tradeOpened: boolean
  tradeClosed: boolean
  systemErrors: boolean
  warnings: boolean
  stopLossHit: boolean
  takeProfitHit: boolean
}

const defaultTriggers: AlertTriggers = {
  tradeOpened: true,
  tradeClosed: true,
  systemErrors: true,
  warnings: true,
  stopLossHit: true,
  takeProfitHit: true,
}

export function NotificationSettings() {
  const { settings, isLoading, updateJSONField } = useSettings()
  const [isAdding, setIsAdding] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [showToken, setShowToken] = useState(false)
  const [currentChannelId, setCurrentChannelId] = useState<string | null>(null)
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [simulatorTradeNotifications, setSimulatorTradeNotifications] = useState(false)
  const [alertTriggers, setAlertTriggers] = useState<AlertTriggers>(defaultTriggers)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [channelToDelete, setChannelToDelete] = useState<{ id: string; name: string } | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    type: "telegram" as "telegram" | "discord" | "email",
    enabled: true,
    botToken: "",
    chatIds: "",
    soundOn: true,
    protectContent: false,
  })

  // Load notification channels and alert triggers from settings
  useEffect(() => {
    if (settings) {
      try {
        let notificationsData;
        if (typeof settings.notifications === 'string') {
          notificationsData = JSON.parse(settings.notifications || "{}")
        } else {
          notificationsData = settings.notifications || {}
        }
        const channelsArray = notificationsData.channels || []
        setChannels(channelsArray)
        setSimulatorTradeNotifications(Boolean(notificationsData.simulator_trade_notifications))

        let triggersData;
        if (typeof settings.alert_triggers === 'string') {
          triggersData = JSON.parse(settings.alert_triggers || "{}")
        } else {
          triggersData = settings.alert_triggers || {}
        }
        setAlertTriggers({ ...defaultTriggers, ...triggersData })
      } catch (e) {
        setChannels([])
        setAlertTriggers(defaultTriggers)
      }
    }
  }, [settings])

  const handleSimulatorToggle = async (checked: boolean) => {
    setSimulatorTradeNotifications(checked)
    try {
      await updateJSONField("notifications", {
        channels,
        simulator_trade_notifications: checked,
      })
    } catch (error) {
      // Error already handled by updateJSONField
    }
  }

  const handleEditClick = (channelId: string) => {
    const channel = channels.find(ch => ch.id === channelId)
    if (channel) {
      setCurrentChannelId(channelId)
      setFormData({
        name: channel.name,
        type: channel.type,
        enabled: channel.enabled,
        botToken: channel.config.botToken || "",
        chatIds: channel.config.chatIds || "",
        soundOn: channel.config.soundOn !== undefined ? channel.config.soundOn : true,
        protectContent: channel.config.protectContent || false,
      })
      setIsEditing(true)
      setIsAdding(false)
    }
  }

  const handleAddClick = () => {
    setCurrentChannelId(null)
    setFormData({
      name: "",
      type: "telegram",
      enabled: true,
      botToken: "",
      chatIds: "",
      soundOn: true,
      protectContent: false,
    })
    setIsAdding(true)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setIsAdding(false)
    setIsEditing(false)
    setCurrentChannelId(null)
  }

  const handleSaveChannel = async () => {
    try {
      let updatedChannels: NotificationChannel[]

      if (isEditing && currentChannelId) {
        // Update existing channel
        updatedChannels = channels.map(ch =>
          ch.id === currentChannelId
            ? {
                ...ch,
                name: formData.name,
                type: formData.type,
                enabled: formData.enabled,
                config: {
                  botToken: formData.botToken,
                  chatIds: formData.chatIds,
                  soundOn: formData.soundOn,
                  protectContent: formData.protectContent,
                }
              }
            : ch
        )
      } else {
        // Add new channel
        const newChannel: NotificationChannel = {
          id: `ch_${Date.now()}`,
          name: formData.name,
          type: formData.type,
          enabled: formData.enabled,
          config: {
            botToken: formData.botToken,
            chatIds: formData.chatIds,
            soundOn: formData.soundOn,
            protectContent: formData.protectContent,
          }
        }
        updatedChannels = [...channels, newChannel]
      }

      // Save to database
      await updateJSONField("notifications", {
        channels: updatedChannels,
        simulator_trade_notifications: simulatorTradeNotifications,
      })

      setChannels(updatedChannels)
      setIsAdding(false)
      setIsEditing(false)
      setCurrentChannelId(null)
    } catch (error) {
      // Error already handled by updateJSONField
    }
  }

  const handleDeleteClick = (channelId: string, channelName: string) => {
    setChannelToDelete({ id: channelId, name: channelName })
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!channelToDelete) return

    try {
      const updatedChannels = channels.filter(ch => ch.id !== channelToDelete.id)
      await updateJSONField("notifications", {
        channels: updatedChannels,
        simulator_trade_notifications: simulatorTradeNotifications,
      })
      setChannels(updatedChannels)
      toast.success("Channel deleted")
    } catch (error) {
      // Error already handled by updateJSONField
    } finally {
      setDeleteDialogOpen(false)
      setChannelToDelete(null)
    }
  }

  const handleClone = async (channelId: string) => {
    try {
      const channelToClone = channels.find(ch => ch.id === channelId)
      if (!channelToClone) return

      // Create a cloned channel with new ID and modified name
      const clonedChannel: NotificationChannel = {
        ...channelToClone,
        id: `ch_${Date.now()}`,
        name: `${channelToClone.name} (Copy)`,
      }

      const updatedChannels = [...channels, clonedChannel]
      await updateJSONField("notifications", {
        channels: updatedChannels,
        simulator_trade_notifications: simulatorTradeNotifications,
      })
      setChannels(updatedChannels)
      toast.success("Channel cloned successfully")
    } catch (error) {
      // Error already handled by updateJSONField
    }
  }

  const handleSaveTriggers = async () => {
    setIsSaving(true)
    try {
      await updateJSONField("alert_triggers", alertTriggers)
    } catch (error) {
      // Error already handled by updateJSONField
    } finally {
      setIsSaving(false)
    }
  }

  const updateTrigger = (key: keyof AlertTriggers, value: boolean) => {
    setAlertTriggers(prev => ({ ...prev, [key]: value }))
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">

      {/* 1. Delivery Channels */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
            <div className="space-y-1.5">
               <CardTitle>Delivery Channels</CardTitle>
               <CardDescription>
                Configure where alerts are sent.
               </CardDescription>
            </div>
            {!isAdding && !isEditing && (
                <Button onClick={handleAddClick} size="sm">
                    <Plus className="mr-2 h-4 w-4" /> Add Channel
                </Button>
            )}
        </CardHeader>
        <CardContent>
            {(isAdding || isEditing) ? (
                <div className="space-y-6 border rounded-md p-4 bg-muted/20">
                    <div className="flex items-center justify-between mb-4">
                        <div className="space-y-1">
                            <h4 className="text-sm font-medium">
                                {isEditing ? "Edit Channel" : "Add Channel"}
                            </h4>
                            <p className="text-xs text-muted-foreground">
                                {isEditing ? "Modify channel configuration" : "Configure a new notification destination"}
                            </p>
                        </div>
                        <Button variant="ghost" size="sm" onClick={handleCancel}>
                            <X className="mr-2 h-4 w-4" /> Cancel
                        </Button>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label>Friendly Name</Label>
                            <Input
                              value={formData.name}
                              onChange={(e) => setFormData({...formData, name: e.target.value})}
                              placeholder="e.g. My Telegram Bot"
                              required
                            />
                        </div>
                         <div className="space-y-2">
                            <Label>Channel Type</Label>
                            <Select
                              value={formData.type}
                              onValueChange={(value: "telegram" | "discord" | "email") => setFormData({...formData, type: value})}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Select type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="telegram">Telegram</SelectItem>
                                    <SelectItem value="discord">Discord</SelectItem>
                                    <SelectItem value="email">Email</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="flex items-center space-x-2">
                        <Switch
                          id="enable-channel"
                          checked={formData.enabled}
                          onCheckedChange={(checked) => setFormData({...formData, enabled: checked})}
                        />
                        <Label htmlFor="enable-channel">Enable this channel</Label>
                    </div>

                    {formData.type === "telegram" && (
                      <div className="space-y-4 pt-2">
                          <h4 className="text-sm font-medium text-blue-500">Telegram Settings</h4>

                          <div className="space-y-2">
                              <Label>Bot Token</Label>
                              <div className="relative">
                                  <Input
                                      type={showToken ? "text" : "password"}
                                      value={formData.botToken}
                                      onChange={(e) => setFormData({...formData, botToken: e.target.value})}
                                      placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
                                  />
                                  <Button
                                      type="button"
                                      variant="ghost"
                                      size="icon"
                                      className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                      onClick={() => setShowToken(!showToken)}
                                  >
                                      {showToken ? (
                                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                                      ) : (
                                          <Eye className="h-4 w-4 text-muted-foreground" />
                                      )}
                                  </Button>
                              </div>
                          </div>

                          <div className="space-y-2">
                              <Label>Chat IDs (comma separated for multiple)</Label>
                              <Input
                                value={formData.chatIds}
                                onChange={(e) => setFormData({...formData, chatIds: e.target.value})}
                                placeholder="123456789,987654321"
                              />
                          </div>

                          <div className="flex items-center justify-between pt-2">
                              <div className="flex items-center space-x-2">
                                  <Switch
                                    id="sound"
                                    checked={formData.soundOn}
                                    onCheckedChange={(checked) => setFormData({...formData, soundOn: checked})}
                                  />
                                  <Label htmlFor="sound">Sound On</Label>
                              </div>
                              <div className="flex items-center space-x-2">
                                  <Switch
                                    id="protect"
                                    checked={formData.protectContent}
                                    onCheckedChange={(checked) => setFormData({...formData, protectContent: checked})}
                                  />
                                  <Label htmlFor="protect">Protect Content</Label>
                              </div>
                          </div>
                      </div>
                    )}

                    <div className="flex justify-end pt-4">
                        <Button onClick={handleSaveChannel}>
                            <Save className="mr-2 h-4 w-4" /> {isEditing ? "Update Channel" : "Create Channel"}
                        </Button>
                    </div>
                </div>
            ) : channels.length > 0 ? (
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Type</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {channels.map((channel) => (
                            <TableRow key={channel.id}>
                                <TableCell className="font-medium flex items-center gap-2">
                                    <MessageSquare className="h-4 w-4 text-blue-500" />
                                    <button
                                        className="hover:underline hover:text-primary focus:outline-none"
                                        onClick={() => handleEditClick(channel.id)}
                                    >
                                        {channel.name}
                                    </button>
                                </TableCell>
                                <TableCell className="capitalize">{channel.type}</TableCell>
                                <TableCell>
                                    <Badge variant="outline" className={channel.enabled ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" : "bg-muted text-muted-foreground"}>
                                        {channel.enabled ? "Active" : "Disabled"}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-right">
                                    <div className="flex items-center justify-end gap-1">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-muted-foreground hover:text-foreground"
                                            onClick={() => handleClone(channel.id)}
                                            title="Clone channel"
                                        >
                                            <Copy className="h-4 w-4" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-8 w-8 text-destructive/70 hover:text-destructive"
                                            onClick={() => handleDeleteClick(channel.id, channel.name)}
                                            title="Delete channel"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </Button>
                                    </div>
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            ) : (
              <div className="flex items-center justify-center p-12 border rounded-md border-dashed bg-muted/30">
                <div className="text-center space-y-2">
                  <p className="text-sm text-muted-foreground">
                    No notification channels configured yet.
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Click "Add Channel" to set up your first notification channel.
                  </p>
                </div>
              </div>
            )}
        </CardContent>
      </Card>

      {/* 1b. Simulator Notifications */}
      <Card>
        <CardHeader>
          <CardTitle>Simulator Alerts</CardTitle>
          <CardDescription>
            Enable browser notifications and sound for simulator trades.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <Label>Simulator trade notifications</Label>
              <p className="text-xs text-muted-foreground">
                Uses browser notifications and local sounds when enabled.
              </p>
            </div>
            <Switch
              checked={simulatorTradeNotifications}
              onCheckedChange={handleSimulatorToggle}
            />
          </div>
        </CardContent>
      </Card>

      {/* 2. Alert Triggers */}
      <Card>
        <CardHeader>
          <CardTitle>Alert Triggers</CardTitle>
          <CardDescription>
            Decide which events justify a notification.
          </CardDescription>
        </CardHeader>
        <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="flex items-center space-x-2">
                    <Checkbox
                      id="alert-open"
                      checked={alertTriggers.tradeOpened}
                      onCheckedChange={(checked) => updateTrigger("tradeOpened", checked as boolean)}
                    />
                    <Label htmlFor="alert-open">Trade Opened</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox
                      id="alert-close"
                      checked={alertTriggers.tradeClosed}
                      onCheckedChange={(checked) => updateTrigger("tradeClosed", checked as boolean)}
                    />
                    <Label htmlFor="alert-close">Trade Closed</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox
                      id="alert-error"
                      checked={alertTriggers.systemErrors}
                      onCheckedChange={(checked) => updateTrigger("systemErrors", checked as boolean)}
                    />
                    <Label htmlFor="alert-error" className="text-red-500">System Errors</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox
                      id="alert-warn"
                      checked={alertTriggers.warnings}
                      onCheckedChange={(checked) => updateTrigger("warnings", checked as boolean)}
                    />
                    <Label htmlFor="alert-warn">Warnings</Label>
                </div>
                <div className="flex items-center space-x-2">
                    <Checkbox
                      id="alert-sl"
                      checked={alertTriggers.stopLossHit}
                      onCheckedChange={(checked) => updateTrigger("stopLossHit", checked as boolean)}
                    />
                    <Label htmlFor="alert-sl">Stop Loss Hit</Label>
                </div>
                 <div className="flex items-center space-x-2">
                    <Checkbox
                      id="alert-tp"
                      checked={alertTriggers.takeProfitHit}
                      onCheckedChange={(checked) => updateTrigger("takeProfitHit", checked as boolean)}
                    />
                    <Label htmlFor="alert-tp">Take Profit Hit</Label>
                </div>
            </div>
        </CardContent>
        <CardFooter className="border-t px-6 py-4 flex justify-end">
             <Button onClick={handleSaveTriggers} disabled={isSaving}>
                {isSaving ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="mr-2 h-4 w-4" />
                    Save Preferences
                  </>
                )}
             </Button>
        </CardFooter>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Notification Channel</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{channelToDelete?.name}"? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

    </div>
  )
}
