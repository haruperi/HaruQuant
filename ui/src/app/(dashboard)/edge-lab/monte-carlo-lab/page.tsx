"use client"

import { MonteCarloSimulation } from "@/components/optimization/monte-carlo-simulation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FlaskConical } from "lucide-react"

export default function MonteCarloLabPage() {
    return (
        <div className="flex flex-col gap-6 p-6">
            <Card>
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <FlaskConical className="h-5 w-5 text-primary" />
                        Monte Carlo Lab
                    </CardTitle>
                    <CardDescription>
                        Perform advanced stress testing on your backtests using Monte Carlo simulations.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <MonteCarloSimulation />
                </CardContent>
            </Card>
        </div>
    )
}
