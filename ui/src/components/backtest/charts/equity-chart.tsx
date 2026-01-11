"use client"

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

const data = Array.from({ length: 100 }, (_, i) => {
  const equity = 10000 + Math.random() * 1000 + (i * 50);
  const drawdown = Math.min(0, Math.random() * -5); // Mock DD percentage
  return {
    name: `Bar ${i}`,
    equity,
    drawdown,
    benchmark: 10000 + (i * 30) // Simple benchmark
  };
});

export function EquityChart() {
  return (
    <Card className="w-full">
        <CardHeader>
            <CardTitle>Performance Charts</CardTitle>
        </CardHeader>
        <CardContent>
            <Tabs defaultValue="equity" className="w-full">
                <div className="flex justify-end mb-4">
                    <TabsList>
                        <TabsTrigger value="equity">Equity Curve</TabsTrigger>
                        <TabsTrigger value="drawdown">Drawdown</TabsTrigger>
                    </TabsList>
                </div>

                <TabsContent value="equity">
                    <div className="h-[400px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                <XAxis dataKey="name" hide />
                                <YAxis domain={['auto', 'auto']} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', color: '#fff' }}
                                    formatter={(value: number) => [`$${value.toFixed(2)}`, 'Equity']}
                                />
                                <Line type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={2} dot={false} />
                                <Line type="monotone" dataKey="benchmark" stroke="#64748b" strokeWidth={1} dot={false} strokeDasharray="5 5" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </TabsContent>

                <TabsContent value="drawdown">
                    <div className="h-[400px] w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                <XAxis dataKey="name" hide />
                                <YAxis />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1e293b', border: 'none', color: '#fff' }}
                                    formatter={(value: number) => [`${value.toFixed(2)}%`, 'Drawdown']}
                                />
                                <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fill="#ef4444" fillOpacity={0.3} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </TabsContent>
            </Tabs>
        </CardContent>
    </Card>
  );
}
