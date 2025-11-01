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
      className="relative h-96 w-full overflow-visible"
    >
      {/* Cards container */}
      <div className="flex flex-col gap-6 md:flex-row md:gap-4 justify-center items-start w-full">
        {/* Card 1 - Campaign Dashboard */}
        <motion.div
          className="relative w-full md:w-80"
          style={{
            rotateX,
            rotateY,
            transformStyle: "preserve-3d",
          } as any}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        >
          <motion.div
            className="relative rounded-3xl bg-gradient-to-br from-purple-600 via-pink-600 to-orange-500 p-6 shadow-lg backdrop-blur-sm border border-white/20 w-full h-[380px]"
            style={{
              transform: "translateZ(0px)",
            } as any}
            animate={{
              y: [0, -12, 0],
            }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
          >
            <div className="relative z-10 h-full flex flex-col">
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

              <div className="space-y-3 flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white/80 text-xs">Active Campaigns</span>
                  <span className="text-white font-semibold">8</span>
                </div>
                <div className="h-2 rounded-full bg-white/30 overflow-hidden">
                  <motion.div
                    className="h-full bg-white/60 rounded-full"
                    initial={{ width: "0%" }}
                    animate={{ width: "72%" }}
                    transition={{ duration: 2, delay: 0.5, ease: "easeOut" }}
                  />
                </div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white/80 text-xs">Content Delivered</span>
                  <span className="text-white font-semibold">156</span>
                </div>
                <div className="h-2 rounded-full bg-white/30 overflow-hidden">
                  <motion.div
                    className="h-full bg-white/60 rounded-full"
                    initial={{ width: "0%" }}
                    animate={{ width: "85%" }}
                    transition={{ duration: 2, delay: 0.7, ease: "easeOut" }}
                  />
                </div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-white/80 text-xs">Avg. Performance</span>
                  <span className="text-white font-semibold">92%</span>
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

              <div className="flex flex-col items-center justify-center mt-4 pt-4 border-t border-white/20">
                <p className="text-white/90 text-sm font-medium">200+ Active Creators</p>
                <p className="text-white/60 text-xs">500+ Campaigns running</p>
              </div>
            </div>
          </motion.div>
        </motion.div>

        {/* Card 2 - Creator Outreach */}
        <motion.div
          className="relative w-full md:w-80 mt-12 md:mt-0"
          style={{
            rotateX,
            rotateY,
            transformStyle: "preserve-3d",
          } as any}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        >
          <motion.div
            className="relative rounded-3xl bg-gradient-to-br from-pink-600 via-orange-500 to-purple-600 p-6 shadow-lg backdrop-blur-sm border border-white/20 w-full h-[380px]"
            style={{
              transform: "translateZ(0px)",
            } as any}
            animate={{
              y: [0, -12, 0],
            }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
          >
            <div className="relative z-10 h-full flex flex-col">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-white text-xl font-bold">Creator Outreach</h3>
                  <p className="text-white/80 text-sm">Automated matching</p>
                </div>
              </div>

              <div className="flex-1 mb-4">
                <p className="text-white/90 font-medium leading-relaxed mb-4">
                  Never spend time reaching out to creators again
                </p>

                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <p className="text-white/90 text-sm">AI-powered matching</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <p className="text-white/90 text-sm">Automated negotiations</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <p className="text-white/90 text-sm">Instant onboarding</p>
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-center justify-center pt-4 border-t border-white/20">
                <p className="text-white/90 text-sm font-medium">Auto Matching</p>
                <p className="text-white/60 text-xs">100% Automated</p>
              </div>
            </div>
          </motion.div>
        </motion.div>

        {/* Card 3 - Viral Content */}
        <motion.div
          className="relative w-full md:w-80 mt-12 md:mt-0"
          style={{
            rotateX,
            rotateY,
            transformStyle: "preserve-3d",
          } as any}
          transition={{ type: "spring", stiffness: 100, damping: 20 }}
        >
          <motion.div
            className="relative rounded-3xl bg-gradient-to-br from-orange-500 via-pink-600 to-purple-600 p-6 shadow-lg backdrop-blur-sm border border-white/20 w-full h-[380px]"
            style={{
              transform: "translateZ(0px)",
            } as any}
            animate={{
              y: [0, -12, 0],
            }}
            transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay: 0.6 }}
          >
            <div className="relative z-10 h-full flex flex-col">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-xl bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-white text-xl font-bold">Viral Content</h3>
                  <p className="text-white/80 text-sm">Performance guaranteed</p>
                </div>
              </div>

              <div className="flex-1 mb-4">
                <p className="text-white/90 font-medium leading-relaxed mb-4">
                  Make your content go viral
                </p>

                <div className="bg-white/10 rounded-xl p-4 space-y-3">
                  <div className="flex items-baseline justify-between">
                    <span className="text-white/80 text-xs">Engagement</span>
                    <span className="text-white text-lg font-bold">+243%</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/20 overflow-hidden">
                    <motion.div
                      className="h-full bg-white/80 rounded-full"
                      initial={{ width: "0%" }}
                      animate={{ width: "85%" }}
                      transition={{ duration: 2, delay: 0.5, ease: "easeOut" }}
                    />
                  </div>
                  <div className="flex items-baseline justify-between">
                    <span className="text-white/80 text-xs">Conversion</span>
                    <span className="text-white text-lg font-bold">+189%</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/20 overflow-hidden">
                    <motion.div
                      className="h-full bg-white/80 rounded-full"
                      initial={{ width: "0%" }}
                      animate={{ width: "65%" }}
                      transition={{ duration: 2, delay: 0.7, ease: "easeOut" }}
                    />
                  </div>
                </div>
              </div>

              <div className="flex flex-col items-center justify-center pt-4 border-t border-white/20">
                <p className="text-white/90 text-sm font-medium">5.7x ROI</p>
                <p className="text-white/60 text-xs">Viral Performance</p>
              </div>
            </div>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
