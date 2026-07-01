export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-5xl w-full items-center justify-between font-mono text-sm lg:flex">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 dark:from-inherit lg:static lg:w-auto  lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
          Academic Analytics Platform Bootstrap
        </p>
      </div>
      <div className="mt-16 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-6xl">
          Foundation <span className="text-muted-foreground">Ready</span>
        </h1>
        <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
          Production-grade Next.js App Router architecture initialized.
          Clean architecture, modular feature slices, and strict typed boundaries.
        </p>
      </div>
    </main>
  );
}
