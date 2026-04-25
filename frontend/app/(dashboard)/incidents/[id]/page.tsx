import { IncidentDetail } from './IncidentDetail';

interface Props {
  params: { id: string };
}

export function generateMetadata({ params }: Props) {
  return { title: `Incident ${params.id.slice(0, 8)} — NOC Center` };
}

export default function IncidentPage({ params }: Props) {
  return <IncidentDetail id={params.id} />;
}
