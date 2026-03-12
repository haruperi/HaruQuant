"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Loader2, Eye, EyeOff } from "lucide-react"
import { toast } from "sonner"

export function LoginForm() {
  const { login } = useAuth()
  const router = useRouter()
  const [isLoading, setIsLoading] = React.useState(false)
  const [username, setUsername] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [showPassword, setShowPassword] = React.useState(false)

  async function onSubmit(event: React.SyntheticEvent) {
    event.preventDefault()
    setIsLoading(true)

    try {
      await login(username, password)
      toast.success("Logged in successfully")
      router.replace("/")
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Invalid credentials. Please try again."
      toast.error("Failed to login", {
        description: errorMessage,
      })
    } finally {
      setIsLoading(false)
    }
  }

  function handleForgotPassword(event: React.MouseEvent) {
    event.preventDefault()
    toast.info("Password Reset", {
      description: "Please contact the administrator to reset your password.",
    })
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-2xl">Login</CardTitle>
        <CardDescription>
          Enter your username and password to access the dashboard.
        </CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="username">Username</Label>
            <Input
                id="username"
                type="text"
                placeholder="johndoe"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <div className="flex items-center">
              <Label htmlFor="password">Password</Label>
              <Link
                className="ml-auto inline-block text-sm underline cursor-pointer"
                href="#"
                onClick={handleForgotPassword}
              >
                Forgot your password?
              </Link>
            </div>
            <div className="relative">
              <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
                <span className="sr-only">Toggle password visibility</span>
              </Button>
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button className="w-full" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Sign In
          </Button>
        </CardFooter>
      </form>
      <div className="px-6 pb-4 text-center text-xs text-muted-foreground">
        <p>
          Don't have an account?{" "}
          <Link href="/register" className="underline hover:text-primary">
            Sign up
          </Link>
        </p>
      </div>
    </Card>
  )
}
