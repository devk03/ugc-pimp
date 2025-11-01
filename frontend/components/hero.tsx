import Link from "next/link";
import { Button } from "./ui/button";
import { hasEnvVars } from "@/lib/utils";
import { Landing3DAnimation } from "./landing-3d-animation";

export function Hero() {
  return (
    <div className="flex flex-col gap-12 items-center text-center px-4 py-12">
      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border bg-card/50 backdrop-blur-sm mb-4">
        <span className="relative flex h-3 w-3">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-purple-500"></span>
        </span>
        <span className="text-sm text-muted-foreground">Now accepting creators</span>
      </div>

      <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight">
        <span className="bg-gradient-to-r from-purple-600 via-pink-600 to-orange-600 bg-clip-text text-transparent">
          Pimp Your Brand
        </span>
        <br />
        <span className="text-foreground">with UGC</span>
      </h1>

      <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl leading-relaxed">
        The easiest way to create, manage, and scale user-generated content campaigns.
        Connect with creators, track performance, and grow your brand authentically.
      </p>

      {/* 3D Animation Section */}
      <div className="w-full max-w-5xl mx-auto mt-12 mb-8">
        <Landing3DAnimation />
      </div>
    </div>
  );
}
