"use client"

import Link from "next/link"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface EdgeLabPrerequisiteStateProps {
  title: string
  description: string
  actionHref: string
  actionLabel: string
}

export function EdgeLabPrerequisiteState({
  title,
  description,
  actionHref,
  actionLabel,
}: EdgeLabPrerequisiteStateProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <Link href={actionHref}>
          <Button>{actionLabel}</Button>
        </Link>
      </CardContent>
    </Card>
  )
}
