"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import * as z from "zod"
import { UploadCloud, FileText } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    CardFooter,
} from "@/components/ui/card"
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { toast } from "sonner"
import { useRouter } from "next/navigation"

const importFormSchema = z.object({
    source: z.string(),
    strategyName: z.string().min(1, "Strategy name is required"),
    symbol: z.string().min(1, "Symbol is required"),
    timeframe: z.string().min(1, "Timeframe is required"),
    alias: z.string(),
    description: z.string(),
    initialBalance: z.any().transform((v) => Number(v)).pipe(z.number().min(1, "Initial balance is required")),
})

type FormValues = z.infer<typeof importFormSchema>

interface BacktestImportFormProps {
    onCancel: () => void
}

const getErrorMessage = (payload: unknown, fallback: string) => {
    if (!payload) return fallback
    if (typeof payload === "string") return payload
    if (payload instanceof Error) return payload.message || fallback

    if (typeof payload === "object" && payload !== null && "detail" in payload) {
        const detail = (payload as { detail?: unknown }).detail
        if (typeof detail === "string") return detail
        if (Array.isArray(detail)) {
            const messages = detail
                .map((item) => {
                    if (!item) return ""
                    if (typeof item === "string") return item
                    if (typeof item === "object") {
                        const message = (item as { msg?: string }).msg
                        const loc = (item as { loc?: unknown }).loc
                        if (message && loc) {
                            const locText = Array.isArray(loc) ? loc.join(".") : String(loc)
                            return `${message} (${locText})`
                        }
                        if (message) return message
                        return JSON.stringify(item)
                    }
                    return String(item)
                })
                .filter(Boolean)
            if (messages.length > 0) return messages.join("; ")
        }
        if (detail && typeof detail === "object") {
            return JSON.stringify(detail)
        }
    }

    return JSON.stringify(payload)
}

export function BacktestImportForm({ onCancel }: BacktestImportFormProps) {
    const router = useRouter()
    const [file, setFile] = useState<File | null>(null)
    const [isSubmitting, setIsSubmitting] = useState(false)

    const form = useForm<FormValues>({
        resolver: zodResolver(importFormSchema),
        defaultValues: {
            source: "strategy_quant_x",
            strategyName: "",
            symbol: "",
            timeframe: "H1",
            alias: "",
            description: "",
            initialBalance: 10000,
        },
    })

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0])
        }
    }

    async function onSubmit(values: FormValues) {
        if (!file) {
            toast.error("Please upload a CSV file.")
            return
        }

        setIsSubmitting(true)
        const formData = new FormData()
        formData.append("file", file)
        formData.append("strategy_name", values.strategyName)
        formData.append("symbol", values.symbol)
        formData.append("timeframe", values.timeframe)
        // Add defaults if missing
        if (values.alias) formData.append("alias", values.alias)
        if (values.description) formData.append("description", values.description)
        formData.append("initial_balance", values.initialBalance.toString())

        try {
            // Determine endpoint based on source
            // Currently only SQX supported
            const endpoint = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/import/sqx`

            const token = localStorage.getItem("hq_auth_token")
            const headers: HeadersInit = {}
            if (token) {
                headers["Authorization"] = `Bearer ${token}`
            }

            const response = await fetch(endpoint, {
                method: "POST",
                body: formData,
                headers,
            })

            if (!response.ok) {
                const raw = await response.text()
                let errorData: unknown = null
                try {
                    errorData = raw ? JSON.parse(raw) : null
                } catch {
                    errorData = raw
                }
                throw new Error(getErrorMessage(errorData, "Import failed"))
            }

            const data = await response.json()
            toast.success("Import Successful", {
                description: `${data.message} ID: ${data.backtest_id}`,
            })

            // Redirect to performance page
            router.push(`/performance?selected=${data.backtest_id}`)

        } catch (error) {
            console.error(error)
            toast.error("Import Failed", {
                description: error instanceof Error ? error.message : "Unknown error",
            })
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <Card className="w-full max-w-2xl mx-auto border-dashed border-2">
            <CardHeader>
                <CardTitle>Import Backtested Trades</CardTitle>
                <CardDescription>
                    Import trade history from external platforms like Strategy Quant X.
                </CardDescription>
            </CardHeader>
            <CardContent>
                <Form {...form}>
                    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">

                        <div className="grid grid-cols-2 gap-4">
                             <FormField
                                control={form.control}
                                name="source"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Source Platform</FormLabel>
                                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select platform" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                <SelectItem value="strategy_quant_x">Strategy Quant X</SelectItem>
                                                <SelectItem value="mt5" disabled>Metatrader 5 (Coming Soon)</SelectItem>
                                                <SelectItem value="myfxbook" disabled>Myfxbook (Coming Soon)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />

                            <FormField
                                control={form.control}
                                name="strategyName"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Strategy Name</FormLabel>
                                        <FormControl>
                                            <Input placeholder="e.g. TrendFollower_V1" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <div className="grid grid-cols-3 gap-4">
                            <FormField
                                control={form.control}
                                name="symbol"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Symbol</FormLabel>
                                        <FormControl>
                                            <Input placeholder="EURUSD" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <FormField
                                control={form.control}
                                name="timeframe"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Timeframe</FormLabel>
                                        <Select onValueChange={field.onChange} defaultValue={field.value}>
                                            <FormControl>
                                                <SelectTrigger>
                                                    <SelectValue placeholder="Select TF" />
                                                </SelectTrigger>
                                            </FormControl>
                                            <SelectContent>
                                                {["M1", "M5", "M15", "M30", "H1", "H4", "D1"].map((tf) => (
                                                    <SelectItem key={tf} value={tf}>
                                                        {tf}
                                                    </SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                             <FormField
                                control={form.control}
                                name="initialBalance"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Initial Balance</FormLabel>
                                        <FormControl>
                                            <Input type="number" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        {/* File Upload Area */}
                        <div className="border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center gap-2 bg-muted/50 hover:bg-muted/80 transition-colors">
                            <UploadCloud className="h-10 w-10 text-muted-foreground" />
                            <div className="text-sm font-medium">
                                {file ? file.name : "Drag & drop or Click to upload CSV"}
                            </div>
                            <Input
                                type="file"
                                accept=".csv"
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                onChange={handleFileChange}
                                style={{ position: 'relative' , zIndex: 10}} // Hack to make it clickable but hidden styles
                            />
                            {/* Since styling input[type=file] is hard, we usually wrap or overlay.
                                For simplicity in this quick implementation, I will just show a standard input below if drag/drop is complex to wire up perfectly right now.
                            */}
                        </div>
                        {/* Fallback standard input ensuring visibility/usability */}
                        {!file && (
                           <div className="flex flex-col gap-2">
                               <FormLabel>CSV File</FormLabel>
                               <Input type="file" accept=".csv" onChange={handleFileChange} />
                           </div>
                        )}


                        <div className="grid grid-cols-2 gap-4">
                             <FormField
                                control={form.control}
                                name="alias"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Alias (Optional)</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Friendly Name" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                             <FormField
                                control={form.control}
                                name="description"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormLabel>Description (Optional)</FormLabel>
                                        <FormControl>
                                            <Input placeholder="Notes..." {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                        </div>

                        <CardFooter className="px-0 flex justify-between pt-4">
                            <Button variant="outline" type="button" onClick={onCancel}>
                                Cancel
                            </Button>
                            <Button type="submit" disabled={isSubmitting}>
                                {isSubmitting ? "Importing..." : "Import Trades"}
                            </Button>
                        </CardFooter>
                    </form>
                </Form>
            </CardContent>
        </Card>
    )
}
