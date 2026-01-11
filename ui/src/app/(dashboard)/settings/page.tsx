"use client"

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { GeneralSettings } from "@/components/settings/general-settings"
import { BrokerSettings } from "@/components/settings/broker-settings"
import { TradingSettings } from "@/components/settings/trading-settings"
import { NotificationSettings } from "@/components/settings/notification-settings"
import { Settings, Shield, Bell, Key, LineChart } from "lucide-react"

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
      </div>

      <Tabs defaultValue="general" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4 lg:w-[400px]">
           <TabsTrigger value="general">
             <Settings className="mr-2 h-4 w-4" /> General
           </TabsTrigger>
           <TabsTrigger value="broker">
             <Key className="mr-2 h-4 w-4" /> Broker
           </TabsTrigger>
           <TabsTrigger value="trading">
             <LineChart className="mr-2 h-4 w-4" /> Trading
           </TabsTrigger>
           <TabsTrigger value="notifications">
             <Bell className="mr-2 h-4 w-4" /> Alerts
           </TabsTrigger>
        </TabsList>

        <TabsContent value="general" className="space-y-4">
          <GeneralSettings />
        </TabsContent>

        <TabsContent value="broker" className="space-y-4">
          <BrokerSettings />
        </TabsContent>

        <TabsContent value="trading" className="space-y-4">
          <TradingSettings />
        </TabsContent>

        <TabsContent value="notifications" className="space-y-4">
          <NotificationSettings />
        </TabsContent>
      </Tabs>
    </div>
  )
}
