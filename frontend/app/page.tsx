import Image from "next/image";

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-100 p-8">
      <Image
        className="dark:invert mb-8"
        src="/next.svg"
        alt="Next.js logo"
        width={180}
        height={38}
        priority
      />
      <h1 className="text-4xl font-bold text-blue-600 text-center">
        Tailwind CSS is working!
      </h1>
      <p className="mt-4 text-lg text-gray-600 text-center">
        Get started by editing{" "}
        <code className="bg-black/[.05] dark:bg-white/[.06] px-1 py-0.5 rounded font-semibold">
          app/page.tsx
        </code>
      </p>
      <div className="flex gap-4 mt-8">
        <a
          className="rounded-lg bg-blue-500 text-white px-6 py-3 text-lg font-medium hover:bg-blue-700 transition"
          href="https://nextjs.org/docs"
          target="_blank"
          rel="noopener noreferrer"
        >
          Read Docs
        </a>
        <a
          className="rounded-lg bg-gray-200 text-gray-800 px-6 py-3 text-lg font-medium hover:bg-gray-300 transition"
          href="https://vercel.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          Deploy Now
        </a>
      </div>
    </div>
  );
}
