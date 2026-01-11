"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
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
import { Trash2, Eye, EyeOff, Save, Plus, X, Loader2, Copy } from "lucide-react"
import { toast } from "sonner"
import { useSettings } from "@/lib/use-settings"

interface BrokerAccount {
  id: string
  name: string
  description?: string
  login: string
  password: string
  server: string
  environment: "demo" | "live"
  type: string
  terminalPath?: string
  isDefault?: boolean
}

export function BrokerSettings() {
  const { settings, isLoading, updateJSONField, getJSONField } = useSettings()
  const [isAdding, setIsAdding] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [currentAccountId, setCurrentAccountId] = useState<string | null>(null)
  const [connectedAccounts, setConnectedAccounts] = useState<BrokerAccount[]>([])
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [accountToDelete, setAccountToDelete] = useState<{ id: string; name: string } | null>(null)

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    login: "",
    password: "",
    server: "",
    environment: "demo" as "demo" | "live",
    terminalPath: "",
    isDefault: false,
  })

  // Load broker accounts from settings
  useEffect(() => {
    if (settings) {
      try {
        let credentials;
        if (typeof settings.broker_credentials === 'string') {
          credentials = JSON.parse(settings.broker_credentials || "{}")
        } else {
          credentials = settings.broker_credentials || {}
        }

        const accountsArray = credentials.accounts || []
        setConnectedAccounts(accountsArray)
      } catch (e) {
        setConnectedAccounts([])
      }
    }
  }, [settings])

  const handleEditClick = (accountId: string) => {
    const account = connectedAccounts.find(acc => acc.id === accountId)
    if (account) {
      setCurrentAccountId(accountId)
      setFormData({
        name: account.name,
        description: account.description || "",
        login: account.login,
        password: account.password,
        server: account.server,
        environment: account.environment,
        terminalPath: account.terminalPath || "",
        isDefault: account.isDefault || false,
      })
      setIsEditing(true)
      setIsAdding(false)
    }
  }

  const handleAddClick = () => {
    setCurrentAccountId(null)
    setFormData({
      name: "",
      description: "",
      login: "",
      password: "",
      server: "",
      environment: "demo",
      terminalPath: "",
      isDefault: false,
    })
    setIsAdding(true)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setIsAdding(false)
    setIsEditing(false)
    setCurrentAccountId(null)
  }

  const handleSave = async () => {
    try {
      let updatedAccounts: BrokerAccount[]

      if (isEditing && currentAccountId) {
        // Update existing account
        updatedAccounts = connectedAccounts.map(acc =>
          acc.id === currentAccountId
            ? { ...acc, ...formData, id: currentAccountId, type: "MT5" }
            : acc
        )
      } else {
        // Add new account
        const newAccount: BrokerAccount = {
          id: `acc_${Date.now()}`,
          ...formData,
          type: "MT5",
        }
        updatedAccounts = [...connectedAccounts, newAccount]
      }

      // Save to database
      await updateJSONField("broker_credentials", { accounts: updatedAccounts })

      setConnectedAccounts(updatedAccounts)
      setIsAdding(false)
      setIsEditing(false)
      setCurrentAccountId(null)
    } catch (error) {
      // Error already handled by updateJSONField
    }
  }

  const handleDeleteClick = (accountId: string, accountName: string) => {
    setAccountToDelete({ id: accountId, name: accountName })
    setDeleteDialogOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (!accountToDelete) return

    try {
      const updatedAccounts = connectedAccounts.filter(acc => acc.id !== accountToDelete.id)
      await updateJSONField("broker_credentials", { accounts: updatedAccounts })
      setConnectedAccounts(updatedAccounts)
      toast.success("Account deleted")
    } catch (error) {
      // Error already handled by updateJSONField
    } finally {
      setDeleteDialogOpen(false)
      setAccountToDelete(null)
    }
  }

  const handleClone = async (accountId: string) => {
    try {
      const accountToClone = connectedAccounts.find(acc => acc.id === accountId)
      if (!accountToClone) return

      // Create a cloned account with new ID and modified name
      const clonedAccount: BrokerAccount = {
        ...accountToClone,
        id: `acc_${Date.now()}`,
        name: `${accountToClone.name} (Copy)`,
        isDefault: false, // Don't copy default status
      }

      const updatedAccounts = [...connectedAccounts, clonedAccount]
      await updateJSONField("broker_credentials", { accounts: updatedAccounts })
      setConnectedAccounts(updatedAccounts)
      toast.success("Account cloned successfully")
    } catch (error) {
      // Error already handled by updateJSONField
    }
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

      {/* 1. Connected Accounts (and Add/Edit Form) */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
            <div className="space-y-1.5">
                <CardTitle>Connected Accounts</CardTitle>
                <CardDescription>
                    Manage your connected exchange and broker accounts.
                </CardDescription>
            </div>
            {!isAdding && !isEditing && (
                <Button variant="outline" size="sm" onClick={handleAddClick}>
                    <Plus className="mr-2 h-4 w-4" /> Add Account
                </Button>
            )}
        </CardHeader>
        <CardContent>
          {(isAdding || isEditing) ? (
             <div className="space-y-4 border rounded-md p-4 bg-muted/20">
                 <div className="flex items-center justify-between mb-4">
                    <div className="space-y-1">
                        <h4 className="text-sm font-medium">
                            {isEditing ? "Edit MetaTrader 5 Account" : "Add MetaTrader 5 Account"}
                        </h4>
                        <p className="text-xs text-muted-foreground">
                            {isEditing ? `Modify configuration for ${formData.name}` : "Configure connection to your terminal"}
                        </p>
                    </div>
                    <Button variant="ghost" size="sm" onClick={handleCancel}>
                        <X className="mr-2 h-4 w-4" /> Cancel
                    </Button>
                 </div>

                <div className="grid gap-2">
                    <Label htmlFor="alias">Account Alias</Label>
                    <Input
                      id="alias"
                      value={formData.name}
                      onChange={(e) => setFormData({...formData, name: e.target.value})}
                      placeholder="e.g. My Demo Account"
                      required
                    />
                </div>

                <div className="grid gap-2">
                    <Label htmlFor="description">Description (Optional)</Label>
                    <Input
                      id="description"
                      value={formData.description}
                      onChange={(e) => setFormData({...formData, description: e.target.value})}
                      placeholder="Notes about this account..."
                    />
                </div>

                <div className="flex items-center space-x-2 py-2">
                    <Switch
                      id="default-account"
                      checked={formData.isDefault}
                      onCheckedChange={(checked) => setFormData({...formData, isDefault: checked})}
                    />
                    <div className="grid gap-1.5 leading-none">
                        <Label htmlFor="default-account">Set as Default Account</Label>
                        <p className="text-sm text-muted-foreground">
                            This account will be selected by default for trading operations.
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                        <Label htmlFor="login">Login ID</Label>
                        <Input
                          id="login"
                          value={formData.login}
                          onChange={(e) => setFormData({...formData, login: e.target.value})}
                          placeholder="12345678"
                          required
                        />
                    </div>
                    <div className="grid gap-2">
                        <Label htmlFor="password">Password</Label>
                        <div className="relative">
                            <Input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                placeholder="••••••"
                                value={formData.password}
                                onChange={(e) => setFormData({...formData, password: e.target.value})}
                                required
                            />
                             <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                                onClick={() => setShowPassword(!showPassword)}
                            >
                                {showPassword ? (
                                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                    <Eye className="h-4 w-4 text-muted-foreground" />
                                )}
                            </Button>
                        </div>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="grid gap-2">
                        <Label htmlFor="server">Server</Label>
                        <Input
                          id="server"
                          value={formData.server}
                          onChange={(e) => setFormData({...formData, server: e.target.value})}
                          placeholder="MetaQuotes-Demo"
                          required
                        />
                    </div>
                     <div className="grid gap-2">
                        <Label htmlFor="env">Environment</Label>
                        <Select
                          value={formData.environment}
                          onValueChange={(value: "demo" | "live") => setFormData({...formData, environment: value})}
                        >
                            <SelectTrigger id="env">
                                <SelectValue placeholder="Select environment" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="demo">Demo</SelectItem>
                                <SelectItem value="live">Live</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="grid gap-2">
                    <Label htmlFor="path">Terminal Path (Optional)</Label>
                    <Input
                      id="path"
                      value={formData.terminalPath}
                      onChange={(e) => setFormData({...formData, terminalPath: e.target.value})}
                      placeholder="C:\Program Files\MetaTrader 5\terminal64.exe"
                    />
                    <p className="text-[0.8rem] text-muted-foreground">
                        Required only if you want the system to launch the terminal automatically.
                    </p>
                </div>

                <div className="pt-4 flex justify-end">
                    <Button onClick={handleSave}>
                        <Save className="mr-2 h-4 w-4" /> {isEditing ? "Update Configuration" : "Save Configuration"}
                    </Button>
                </div>
             </div>
          ) : connectedAccounts.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Environment</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {connectedAccounts.map((account) => (
                    <TableRow key={account.id}>
                      <TableCell className="font-medium">
                          <button
                            className="hover:underline hover:text-primary focus:outline-none"
                            onClick={() => handleEditClick(account.id)}
                          >
                            {account.name}
                          </button>
                      </TableCell>
                      <TableCell>{account.type}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className={account.environment === 'live' ? 'bg-destructive/10 text-destructive border-destructive/20' : 'bg-muted text-muted-foreground'}>
                            {account.environment}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-muted-foreground hover:text-foreground"
                              onClick={() => handleClone(account.id)}
                              title="Clone account"
                          >
                              <Copy className="h-4 w-4" />
                          </Button>
                          <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-destructive/70 hover:text-destructive"
                              onClick={() => handleDeleteClick(account.id, account.name)}
                              title="Delete account"
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
                  No broker accounts connected yet.
                </p>
                <p className="text-xs text-muted-foreground">
                  Click "Add Account" to connect your first broker.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2. Exchange Connections Placeholder */}
      <Card>
        <CardHeader>
          <CardTitle>Exchange Connections</CardTitle>
          <CardDescription>
            Connect to crypto exchanges and data providers.
          </CardDescription>
        </CardHeader>
        <CardContent>
            <div className="flex items-center justify-center p-6 border rounded-md border-dashed bg-muted/30">
                <p className="text-sm text-muted-foreground">
                    Integration with Binance, Kraken, and other exchanges coming soon.
                </p>
            </div>
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Broker Account</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{accountToDelete?.name}"? This action cannot be undone.
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
