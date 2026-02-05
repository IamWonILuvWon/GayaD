import JobStatus from "./JobStatus";

type Props = {
  params: { id: string };
};

export default async function Page({ params }: Props) {
  const { id } = await params;

  return (
    <main>
      <section className="pt-10">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-3xl font-semibold mb-6">작업 상세</h1>
          <JobStatus id={id} />
        </div>
      </section>
    </main>
  );
}
