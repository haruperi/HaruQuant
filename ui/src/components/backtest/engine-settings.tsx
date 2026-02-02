"use client"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface EngineSettingsProps {
    values: {
        initialCapital: number
        commission: number
        slippageType: "fixed" | "variable"
        slippage: number
        slippageMin: number
        slippageMax: number
        spreadType: "use-broker" | "fixed" | "variable"
        spread: number
        spreadMin: number
        spreadMax: number
        leverage: number
        engineType: "vectorized" | "event-driven"
        dataResolution: "trading_timeframe" | "m1_ohlc" | "synthetic_ticks" | "real_ticks"
    }
    onChange: (key: string, value: any) => void
}

export function EngineSettings({ values, onChange }: EngineSettingsProps) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="text-lg">Engine Settings</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="engineType">Engine Type</Label>
                        <Select
                            value={values.engineType}
                            onValueChange={(val) => onChange("engineType", val)}
                        >
                            <SelectTrigger id="engineType">
                                <SelectValue placeholder="Select Engine" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="vectorized">Vectorized (Fast)</SelectItem>
                                <SelectItem value="event-driven">Event-Driven (Detailed)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="dataResolution">Data Resolution</Label>
                        <Select
                            value={values.dataResolution}
                            onValueChange={(val) => onChange("dataResolution", val)}
                        >
                            <SelectTrigger id="dataResolution">
                                <SelectValue placeholder="Select Resolution" />
                            </SelectTrigger>
                            <SelectContent>
                            <SelectItem value="trading_timeframe">Trading Timeframe (Fast)</SelectItem>
                            <SelectItem value="m1_ohlc">M1 OHLC (Bar Ticks)</SelectItem>
                            <SelectItem value="synthetic_ticks">Synthetic Ticks (M1)</SelectItem>
                            <SelectItem value="real_ticks">Real Ticks (Slowest)</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-2">
                        <Label htmlFor="initialCapital">Initial Capital ($)</Label>
                        <Input
                            id="initialCapital"
                            type="number"
                            value={values.initialCapital}
                            onChange={(e) => onChange("initialCapital", parseFloat(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="commission">Commission (per lot)</Label>
                        <Input
                            id="commission"
                            type="number"
                            value={values.commission}
                            onChange={(e) => onChange("commission", parseFloat(e.target.value))}
                        />
                    </div>
                    <div className="space-y-2">
                        <Label htmlFor="leverage">Leverage</Label>
                        <Input
                            id="leverage"
                            type="number"
                            min="1"
                            step="1"
                            value={values.leverage}
                            onChange={(e) => onChange("leverage", parseInt(e.target.value) || 1)}
                        />
                    </div>
                </div>

                {/* Slippage Section */}
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="slippageType">Slippage Type</Label>
                            <Select
                                value={values.slippageType}
                                onValueChange={(val) => onChange("slippageType", val)}
                            >
                                <SelectTrigger id="slippageType">
                                    <SelectValue placeholder="Select Slippage Type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="fixed">Fixed</SelectItem>
                                    <SelectItem value="variable">Variable (Random)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {values.slippageType === "fixed" ? (
                            <div className="space-y-2">
                                <Label htmlFor="slippage">Slippage (points)</Label>
                                <Input
                                    id="slippage"
                                    type="number"
                                    step="1"
                                    min="0"
                                    value={values.slippage}
                                    onChange={(e) => onChange("slippage", parseInt(e.target.value) || 0)}
                                />
                            </div>
                        ) : (
                            <>
                                <div className="space-y-2">
                                    <Label htmlFor="slippageMin">Slippage Min (points)</Label>
                                    <Input
                                        id="slippageMin"
                                        type="number"
                                        step="1"
                                        min="0"
                                        value={values.slippageMin}
                                        onChange={(e) => onChange("slippageMin", parseInt(e.target.value) || 0)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="slippageMax">Slippage Max (points)</Label>
                                    <Input
                                        id="slippageMax"
                                        type="number"
                                        step="1"
                                        min="0"
                                        value={values.slippageMax}
                                        onChange={(e) => onChange("slippageMax", parseInt(e.target.value) || 0)}
                                    />
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Spread Section */}
                <div className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="spreadType">Spread Type</Label>
                            <Select
                                value={values.spreadType}
                                onValueChange={(val) => onChange("spreadType", val)}
                            >
                                <SelectTrigger id="spreadType">
                                    <SelectValue placeholder="Select Spread Type" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="use-broker">Use Broker (from data)</SelectItem>
                                    <SelectItem value="fixed">Fixed</SelectItem>
                                    <SelectItem value="variable">Variable (Random)</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>

                        {values.spreadType === "fixed" && (
                            <div className="space-y-2">
                                <Label htmlFor="spread">Spread (points)</Label>
                                <Input
                                    id="spread"
                                    type="number"
                                    step="1"
                                    min="0"
                                    value={values.spread}
                                    onChange={(e) => onChange("spread", parseInt(e.target.value) || 0)}
                                />
                            </div>
                        )}

                        {values.spreadType === "variable" && (
                            <>
                                <div className="space-y-2">
                                    <Label htmlFor="spreadMin">Spread Min (points)</Label>
                                    <Input
                                        id="spreadMin"
                                        type="number"
                                        step="1"
                                        min="0"
                                        value={values.spreadMin}
                                        onChange={(e) => onChange("spreadMin", parseInt(e.target.value) || 0)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="spreadMax">Spread Max (points)</Label>
                                    <Input
                                        id="spreadMax"
                                        type="number"
                                        step="1"
                                        min="0"
                                        value={values.spreadMax}
                                        onChange={(e) => onChange("spreadMax", parseInt(e.target.value) || 0)}
                                    />
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </CardContent>
        </Card>
    )
}
