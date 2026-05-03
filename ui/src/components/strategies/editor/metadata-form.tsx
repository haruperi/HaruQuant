"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Switch } from "@/components/ui/switch"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { Plus, Trash2 } from "lucide-react"
import { useEffect, useState } from "react"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface MetadataFormProps {
    metadata: {
        name: string
        description: string
        status: "active" | "inactive" | "testing"
        category: string
        parameters: Record<string, unknown>
        parameterTypes: Record<string, string>
        symbol: string
        timeframe: string
        type: string
        moneyManagement: Record<string, unknown>
        variables: Record<string, unknown>
        variableTypes: Record<string, string>
    }
    onChange: (metadata: MetadataFormProps["metadata"]) => void
}

export function MetadataForm({ metadata, onChange }: MetadataFormProps) {
    const [paramTypeOverrides, setParamTypeOverrides] = useState<Record<string, string>>({})
    const [varTypeOverrides, setVarTypeOverrides] = useState<Record<string, string>>({})

    useEffect(() => {
        if (metadata.parameterTypes) {
            setParamTypeOverrides(metadata.parameterTypes)
        }
    }, [metadata.parameterTypes])

    useEffect(() => {
        if (metadata.variableTypes) {
            setVarTypeOverrides(metadata.variableTypes)
        }
    }, [metadata.variableTypes])

    const getEffectiveType = (value: unknown, key: string, overrides: Record<string, string>): string => {
        if (overrides[key]) return overrides[key]

        if (typeof value === 'boolean') return 'boolean'
        if (typeof value === 'string') return 'string'
        if (typeof value === 'number') {
            return Number.isInteger(value) ? 'int' : 'float'
        }
        return 'string'
    }

    const handleFieldChange = (field: keyof typeof metadata, value: unknown) => {
        onChange({ ...metadata, [field]: value })
    }

    const handleParameterChange = (key: string, value: unknown) => {
        onChange({
            ...metadata,
            parameters: { ...metadata.parameters, [key]: value }
        })
    }

    const handleParameterDelete = (key: string) => {
        const newParams = { ...metadata.parameters }
        delete newParams[key]

        const newOverrides = { ...(metadata.parameterTypes || {}) }
        delete newOverrides[key]
        setParamTypeOverrides(newOverrides)

        onChange({ ...metadata, parameters: newParams, parameterTypes: newOverrides })
    }

    const handleParameterAdd = () => {
        const newKey = `param_${Object.keys(metadata.parameters).length + 1}`
        onChange({
            ...metadata,
            parameters: { ...metadata.parameters, [newKey]: 0 }
        })
    }

    const handleParameterKeyRename = (oldKey: string, newKey: string) => {
        if (oldKey === newKey || !newKey.trim()) return

        const newParams = { ...metadata.parameters }
        const value = newParams[oldKey]
        delete newParams[oldKey]
        newParams[newKey] = value

        const newOverrides = { ...(metadata.parameterTypes || {}) }
        if (newOverrides[oldKey]) {
            newOverrides[newKey] = newOverrides[oldKey]
            delete newOverrides[oldKey]
        }
        setParamTypeOverrides(newOverrides)

        onChange({ ...metadata, parameters: newParams, parameterTypes: newOverrides })
    }

    const handleParameterTypeChange = (key: string, newType: string) => {
        const currentValue = metadata.parameters[key]
        let convertedValue: any

        switch (newType) {
            case 'int':
                convertedValue = parseInt(String(currentValue)) || 0
                break
            case 'float':
                convertedValue = parseFloat(String(currentValue)) || 0.0
                break
            case 'string':
                convertedValue = String(currentValue)
                break
            case 'boolean':
                convertedValue = Boolean(currentValue)
                break
            default:
                convertedValue = currentValue
        }

        const nextOverrides = { ...(metadata.parameterTypes || {}), [key]: newType }
        setParamTypeOverrides(nextOverrides)

        onChange({
            ...metadata,
            parameters: { ...metadata.parameters, [key]: convertedValue },
            parameterTypes: nextOverrides
        })
    }

    const handleVariableChange = (key: string, value: any) => {
        onChange({
            ...metadata,
            variables: { ...(metadata.variables || {}), [key]: value }
        })
    }

    const handleVariableDelete = (key: string) => {
        const newVars = { ...(metadata.variables || {}) }
        delete newVars[key]

        const newOverrides = { ...(metadata.variableTypes || {}) }
        delete newOverrides[key]
        setVarTypeOverrides(newOverrides)

        onChange({ ...metadata, variables: newVars, variableTypes: newOverrides })
    }

    const handleVariableAdd = () => {
        const newKey = `var_${Object.keys(metadata.variables || {}).length + 1}`
        onChange({
            ...metadata,
            variables: { ...(metadata.variables || {}), [newKey]: 0 }
        })
    }

    const handleVariableKeyRename = (oldKey: string, newKey: string) => {
        if (oldKey === newKey || !newKey.trim()) return

        const newVars = { ...(metadata.variables || {}) }
        const value = newVars[oldKey]
        delete newVars[oldKey]
        newVars[newKey] = value

        const newOverrides = { ...(metadata.variableTypes || {}) }
        if (newOverrides[oldKey]) {
            newOverrides[newKey] = newOverrides[oldKey]
            delete newOverrides[oldKey]
        }
        setVarTypeOverrides(newOverrides)

        onChange({ ...metadata, variables: newVars, variableTypes: newOverrides })
    }

    const handleVariableTypeChange = (key: string, newType: string) => {
        const currentValue = metadata.variables?.[key]
        let convertedValue: any

        switch (newType) {
            case 'int':
                convertedValue = parseInt(String(currentValue)) || 0
                break
            case 'float':
                convertedValue = parseFloat(String(currentValue)) || 0.0
                break
            case 'string':
                convertedValue = String(currentValue)
                break
            case 'boolean':
                convertedValue = Boolean(currentValue)
                break
            default:
                convertedValue = currentValue
        }

        const nextOverrides = { ...(metadata.variableTypes || {}), [key]: newType }
        setVarTypeOverrides(nextOverrides)

        onChange({
            ...metadata,
            variables: { ...(metadata.variables || {}), [key]: convertedValue },
            variableTypes: nextOverrides
        })
    }

    return (
        <div className="space-y-6 overflow-y-auto p-1 h-full">
            <Card>
                <CardHeader>
                    <CardTitle>Strategy Info</CardTitle>
                    <CardDescription>Basic configuration and market context.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="name">Name</Label>
                            <Input
                                id="name"
                                value={metadata.name}
                                onChange={(e) => handleFieldChange("name", e.target.value)}
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="type">Type</Label>
                            <Select
                                value={metadata.type || "MetaTrader5 (hedged)"}
                                onValueChange={(value) => handleFieldChange("type", value)}
                            >
                                <SelectTrigger id="type">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="MetaTrader5 (hedged)">MetaTrader5 (hedged)</SelectItem>
                                    <SelectItem value="MetaTrader5 (netting)">MetaTrader5 (netting)</SelectItem>
                                    <SelectItem value="Backtest">Backtest</SelectItem>
                                    <SelectItem value="Live Trading">Live Trading</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="symbol">Symbol</Label>
                            <Input
                                id="symbol"
                                value={metadata.symbol || ""}
                                onChange={(e) => handleFieldChange("symbol", e.target.value)}
                                placeholder="EURUSD"
                            />
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="timeframe">Timeframe</Label>
                            <Select
                                value={metadata.timeframe || "H1"}
                                onValueChange={(value) => handleFieldChange("timeframe", value)}
                            >
                                <SelectTrigger id="timeframe">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="M1">M1 (1 minute)</SelectItem>
                                    <SelectItem value="M5">M5 (5 minutes)</SelectItem>
                                    <SelectItem value="M15">M15 (15 minutes)</SelectItem>
                                    <SelectItem value="M30">M30 (30 minutes)</SelectItem>
                                    <SelectItem value="H1">H1 (1 hour)</SelectItem>
                                    <SelectItem value="H4">H4 (4 hours)</SelectItem>
                                    <SelectItem value="D1">D1 (Daily)</SelectItem>
                                    <SelectItem value="W1">W1 (Weekly)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </div>

                    <div className="grid gap-2">
                        <Label htmlFor="desc">Description</Label>
                        <Textarea
                            id="desc"
                            value={metadata.description}
                            onChange={(e) => handleFieldChange("description", e.target.value)}
                            rows={4}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label htmlFor="status">Status</Label>
                            <Select
                                value={metadata.status}
                                onValueChange={(value) => handleFieldChange("status", value)}
                            >
                                <SelectTrigger id="status">
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="active">Active</SelectItem>
                                    <SelectItem value="inactive">Inactive</SelectItem>
                                    <SelectItem value="testing">Testing</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                        <div className="grid gap-2">
                            <Label htmlFor="category">Category</Label>
                            <Input
                                id="category"
                                value={metadata.category || ""}
                                onChange={(e) => handleFieldChange("category", e.target.value)}
                                placeholder="Trend Following"
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            <Card>
                 <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Parameters</CardTitle>
                        <CardDescription>Optimization variables.</CardDescription>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleParameterAdd}>
                        <Plus className="mr-2 h-4 w-4" /> Add Param
                    </Button>
                </CardHeader>
                <CardContent>
                    {Object.keys(metadata.parameters).length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-8">
                            No parameters defined. Click "Add Param" to add one.
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[150px]">Key</TableHead>
                                    <TableHead>Default</TableHead>
                                    <TableHead className="w-[110px]">Type</TableHead>
                                    <TableHead className="w-[50px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {Object.entries(metadata.parameters).map(([key, value]) => (
                                    <TableRow key={key}>
                                        <TableCell>
                                            <Input
                                                value={key}
                                                className="h-8"
                                                onChange={(e) => handleParameterKeyRename(key, e.target.value)}
                                                placeholder="parameter_name"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Input
                                                value={String(value)}
                                                className="h-8"
                                                type={getEffectiveType(value, key, paramTypeOverrides) === 'boolean' ? 'text' : (getEffectiveType(value, key, paramTypeOverrides) === 'string' ? 'text' : 'number')}
                                                onChange={(e) => {
                                                    const type = getEffectiveType(value, key, paramTypeOverrides)
                                                    let newValue: any = e.target.value
                                                    if (type === 'int') newValue = parseInt(e.target.value) || 0
                                                    else if (type === 'float') newValue = e.target.value // Keep as string to allow "0." and decimals
                                                    else if (type === 'boolean') newValue = e.target.value === 'true'
                                                    handleParameterChange(key, newValue)
                                                }}
                                                onBlur={(e) => {
                                                    const type = getEffectiveType(value, key, paramTypeOverrides)
                                                    if (type === 'float') {
                                                        const parsed = parseFloat(e.target.value)
                                                        if (!Number.isNaN(parsed)) {
                                                            handleParameterChange(key, parsed)
                                                        }
                                                    }
                                                }}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Select
                                                value={getEffectiveType(value, key, paramTypeOverrides)}
                                                onValueChange={(newType) => handleParameterTypeChange(key, newType)}
                                            >
                                                <SelectTrigger className="h-8 w-[90px]">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="int">int</SelectItem>
                                                    <SelectItem value="float">float</SelectItem>
                                                    <SelectItem value="string">string</SelectItem>
                                                    <SelectItem value="boolean">boolean</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 text-destructive"
                                                onClick={() => handleParameterDelete(key)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>

            <Card>
                 <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                        <CardTitle>Variables</CardTitle>
                        <CardDescription>Internal state and custom variables.</CardDescription>
                    </div>
                    <Button variant="outline" size="sm" onClick={handleVariableAdd}>
                        <Plus className="mr-2 h-4 w-4" /> Add Variable
                    </Button>
                </CardHeader>
                <CardContent>
                    {Object.keys(metadata.variables || {}).length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-8">
                            No variables defined. Click "Add Variable" to add one.
                        </p>
                    ) : (
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead className="w-[150px]">Key</TableHead>
                                    <TableHead>Default</TableHead>
                                    <TableHead className="w-[110px]">Type</TableHead>
                                    <TableHead className="w-[50px]"></TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {Object.entries(metadata.variables || {}).map(([key, value]) => (
                                    <TableRow key={key}>
                                        <TableCell>
                                            <Input
                                                value={key}
                                                className="h-8"
                                                onChange={(e) => handleVariableKeyRename(key, e.target.value)}
                                                placeholder="variable_name"
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Input
                                                value={String(value)}
                                                className="h-8"
                                                type={getEffectiveType(value, key, varTypeOverrides) === 'boolean' ? 'text' : (getEffectiveType(value, key, varTypeOverrides) === 'string' ? 'text' : 'number')}
                                                onChange={(e) => {
                                                    const type = getEffectiveType(value, key, varTypeOverrides)
                                                    let newValue: any = e.target.value
                                                    if (type === 'int') newValue = parseInt(e.target.value) || 0
                                                    else if (type === 'float') newValue = e.target.value // Keep as string to allow "0." and decimals
                                                    else if (type === 'boolean') newValue = e.target.value === 'true'
                                                    handleVariableChange(key, newValue)
                                                }}
                                            />
                                        </TableCell>
                                        <TableCell>
                                            <Select
                                                value={getEffectiveType(value, key, varTypeOverrides)}
                                                onValueChange={(newType) => handleVariableTypeChange(key, newType)}
                                            >
                                                <SelectTrigger className="h-8 w-[90px]">
                                                    <SelectValue />
                                                </SelectTrigger>
                                                <SelectContent>
                                                    <SelectItem value="int">int</SelectItem>
                                                    <SelectItem value="float">float</SelectItem>
                                                    <SelectItem value="string">string</SelectItem>
                                                    <SelectItem value="boolean">boolean</SelectItem>
                                                </SelectContent>
                                            </Select>
                                        </TableCell>
                                        <TableCell>
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="h-8 w-8 text-destructive"
                                                onClick={() => handleVariableDelete(key)}
                                            >
                                                <Trash2 className="h-4 w-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
