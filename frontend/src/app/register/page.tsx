"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/lib/auth/auth-context";

const schema = z.object({
  agency_name: z.string().min(2, "Ajans adi en az 2 karakter olmali."),
  email: z.string().email("Gecerli bir e-posta girin."),
  password: z.string().min(8, "Sifre en az 8 karakter olmali."),
});

type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const { register: registerAccount } = useAuth();
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setIsSubmitting(true);
    try {
      await registerAccount(values.email, values.password, values.agency_name);
      router.replace("/brands");
    } catch {
      toast.error("Kayit basarisiz", {
        description: "Bilgileri kontrol edip tekrar deneyin (bu e-posta zaten kayitli olabilir).",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-1 items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="font-mono">Ajans olustur</CardTitle>
          <CardDescription>Yeni bir ajans hesabi ve kullanici olustur.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="agency_name">Ajans adi</Label>
              <Input
                id="agency_name"
                autoComplete="organization"
                aria-invalid={Boolean(errors.agency_name)}
                {...register("agency_name")}
              />
              {errors.agency_name && (
                <p className="text-sm text-destructive">{errors.agency_name.message}</p>
              )}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">E-posta</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                aria-invalid={Boolean(errors.email)}
                {...register("email")}
              />
              {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Sifre</Label>
              <Input
                id="password"
                type="password"
                autoComplete="new-password"
                aria-invalid={Boolean(errors.password)}
                {...register("password")}
              />
              {errors.password && (
                <p className="text-sm text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" disabled={isSubmitting} className="mt-2 cursor-pointer">
              {isSubmitting && <Loader2 className="size-4 animate-spin" />}
              Hesap olustur
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            Zaten hesabin var mi?{" "}
            <Link href="/login" className="text-accent hover:underline">
              Giris yap
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
