"use client";

import React, { useRef, useState, useEffect } from "react";
import { motion } from "framer-motion";

export function Landing3DAnimation() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [rotateX, setRotateX] = useState(0);
  const [rotateY, setRotateY] = useState(0);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const x = (e.clientX - centerX) / (rect.width / 2);
      const y = (e.clientY - centerY) / (rect.height / 2);

      setRotateY(x * 8);
      setRotateX(-y * 8);
    };

    const handleMouseLeave = () => {
      setRotateX(0);
      setRotateY(0);
    };

    const container = containerRef.current;
    if (container) {
      container.addEventListener("mousemove", handleMouseMove);
      container.addEventListener("mouseleave", handleMouseLeave);
    }

    return () => {
      if (container) {
        container.removeEventListener("mousemove", handleMouseMove);
        container.removeEventListener("mouseleave", handleMouseLeave);
      }
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className="relative h-96 w-full flex items-center justify-center overflow-visible"
    >
      {/* Main floating card */}
      <motion.div
        className="relative w-full max-w-md"
        style={{
          rotateX,
          rotateY,
          transformStyle: "preserve-3d",
        } as any}
        transition={{ type: "spring", stiffness: 100, damping: 20 }}
      >
        {/* Primary card */}
        <motion.div
          className="relative rounded-3xl bg-gradient-to-br from-purple-600 via-pink-600 to-orange-500 p-8 shadow-2xl backdrop-blur-sm border border-white/20"
          style={{
            transform: "translateZ(0px)",
          } as any}
          animate={{
            y: [0, -12, 0],
            boxShadow: [
              "0 25px 50px -12px rgba(168, 85, 247, 0.25)",
              "0 35px 60px -12px rgba(236, 72, 153, 0.35)",
              "0 25px 50px -12px rgba(168, 85, 247, 0.25)",
            ],
          }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        >
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <h3 className="text-white text-xl font-bold">Campaign Dashboard</h3>
                <p className="text-white/80 text-sm">All your UGC in one place</p>
              </div>
            </div>
            
            <div className="space-y-3">
              <div className="h-2 rounded-full bg-white/30 overflow-hidden">
                <motion.div
                  className="h-full bg-white/60 rounded-full"
                  initial={{ width: "0%" }}
                  animate={{ width: "72%" }}
                  transition={{ duration: 2, delay: 0.5, ease: "easeOut" }}
                />
              </div>
              <div className="h-2 rounded-full bg-white/30 overflow-hidden">
                <motion.div
                  className="h-full bg-white/60 rounded-full"
                  initial={{ width: "0%" }}
                  animate={{ width: "85%" }}
                  transition={{ duration: 2, delay: 0.7, ease: "easeOut" }}
                />
              </div>
              <div className="h-2 rounded-full bg-white/30 overflow-hidden">
                <motion.div
                  className="h-full bg-white/60 rounded-full"
                  initial={{ width: "0%" }}
                  animate={{ width: "68%" }}
                  transition={{ duration: 2, delay: 0.9, ease: "easeOut" }}
                />
              </div>
            </div>

            <div className="flex items-center gap-4 mt-6 pt-6 border-t border-white/20">
              <div className="flex -space-x-2">
                {[1, 2, 3].map((i) => (
                  <motion.div
                    key={i}
                    className="w-8 h-8 rounded-full bg-white/30 border-2 border-white/50 backdrop-blur-sm"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 1 + i * 0.1, type: "spring" }}
                  />
                ))}
              </div>
              <div className="flex-1">
                <p className="text-white/90 text-sm font-medium">12 Active Creators</p>
                <p className="text-white/60 text-xs">8 Campaigns running</p>
              </div>
            </div>
          </div>

          {/* Shine effect */}
          <motion.div
            className="absolute inset-0 rounded-3xl bg-gradient-to-r from-transparent via-white/10 to-transparent"
            animate={{
              x: ["-100%", "200%"],
            }}
            transition={{
              duration: 3,
              repeat: Infinity,
              repeatDelay: 2,
              ease: "easeInOut",
            }}
            style={{
              transform: "skewX(-20deg)",
            }}
          />
        </motion.div>

        {/* Decorative gradient orbs */}
        <motion.div
          className="absolute -top-10 -right-10 w-32 h-32 rounded-full bg-gradient-to-br from-purple-400/30 to-pink-400/30 blur-2xl"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.4, 0.6, 0.4],
          }}
          transition={{ duration: 4, repeat: Infinity }}
        />
        <motion.div
          className="absolute -bottom-10 -left-10 w-40 h-40 rounded-full bg-gradient-to-br from-pink-400/20 to-orange-400/20 blur-3xl"
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{ duration: 5, repeat: Infinity, delay: 1 }}
        />
      </motion.div>
    </div>
  );
}
