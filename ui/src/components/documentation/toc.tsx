"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

interface TOCItem {
  id: string
  text: string
  level: number
}

interface TableOfContentsProps {
  items: TOCItem[]
}

export function TableOfContents({ items }: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>("")

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id)
          }
        })
      },
      { rootMargin: "-100px 0% -66% 0%" }
    )

    items.forEach((item) => {
      const element = document.getElementById(item.id)
      if (element) {
        observer.observe(element)
      }
    })

    return () => {
      items.forEach((item) => {
        const element = document.getElementById(item.id)
        if (element) {
          observer.unobserve(element)
        }
      })
    }
  }, [items])

  if (items.length === 0) return null

  return (
    <div className="space-y-2">
      <p className="font-medium text-sm">On This Page</p>
      <ul className="m-0 list-none space-y-1 text-sm">
        {items.map((item) => (
          <li key={item.id} className="mt-0 pt-1">
            <a
              href={`#${item.id}`}
              className={cn(
                "inline-block no-underline transition-colors hover:text-foreground",
                item.level === 3 ? "pl-4" : "",
                item.id === activeId
                  ? "font-medium text-foreground"
                  : "text-muted-foreground"
              )}
              onClick={(e) => {
                  e.preventDefault()
                  const element = document.getElementById(item.id);
                  if (element) {
                      element.scrollIntoView({ behavior: 'smooth' });
                      setActiveId(item.id);
                      window.history.pushState(null, '', `#${item.id}`);
                  }
              }}
            >
              {item.text}
            </a>
          </li>
        ))}
      </ul>
    </div>
  )
}
