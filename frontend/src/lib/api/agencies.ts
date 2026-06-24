import { apiClient } from "@/lib/api/client";
import type { AgencyMembership, Paginated } from "@/lib/api/types";

export async function listAgencyMembers(agencyId: string) {
  const { data } = await apiClient.get<Paginated<AgencyMembership>>(
    `/agencies/${agencyId}/members/`
  );
  return data;
}

export async function inviteMember(agencyId: string, email: string) {
  const { data } = await apiClient.post<AgencyMembership>(
    `/agencies/${agencyId}/members/invite/`,
    { email }
  );
  return data;
}

export async function removeMember(agencyId: string, membershipId: string) {
  await apiClient.delete(`/agencies/${agencyId}/members/${membershipId}/`);
}
