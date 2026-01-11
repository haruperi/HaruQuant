export default function DocumentationPage() {
    return (
        <div className="flex-1 p-6">
            <div className="space-y-6">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">System Documentation</h2>
                    <p className="text-muted-foreground">
                        Select a category from the navigation above to view specific documentation.
                    </p>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {/* Placeholder content cards */}
                    <div className="rounded-xl border bg-card text-card-foreground shadow">
                        <div className="p-6 pt-6">
                             <h3 className="font-semibold leading-none tracking-tight mb-2">Fundamentals</h3>
                             <p className="text-sm text-muted-foreground">Core concepts and principles.</p>
                        </div>
                    </div>
                     <div className="rounded-xl border bg-card text-card-foreground shadow">
                        <div className="p-6 pt-6">
                             <h3 className="font-semibold leading-none tracking-tight mb-2">Development</h3>
                             <p className="text-sm text-muted-foreground">Guides for developing strategies and extending the system.</p>
                        </div>
                    </div>
                     <div className="rounded-xl border bg-card text-card-foreground shadow">
                        <div className="p-6 pt-6">
                             <h3 className="font-semibold leading-none tracking-tight mb-2">Trading</h3>
                             <p className="text-sm text-muted-foreground">Live trading operations and management.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
