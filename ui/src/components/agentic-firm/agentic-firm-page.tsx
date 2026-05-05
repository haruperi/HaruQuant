type Section = {
  title: string
  items: string[]
}

type AgenticFirmPageProps = {
  title: string
  subtitle: string
  status: string
  sections: Section[]
}

export function AgenticFirmPage({ title, subtitle, status, sections }: AgenticFirmPageProps) {
  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 p-6">
      <div className="flex flex-col gap-2 border-b pb-4">
        <div className="text-sm font-medium text-emerald-600">{status}</div>
        <h1 className="text-2xl font-semibold tracking-normal">{title}</h1>
        <p className="max-w-3xl text-sm text-muted-foreground">{subtitle}</p>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sections.map((section) => (
          <section key={section.title} className="rounded border bg-background p-4">
            <h2 className="text-sm font-semibold">{section.title}</h2>
            <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
              {section.items.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </main>
  )
}
