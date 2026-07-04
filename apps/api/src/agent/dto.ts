export class AskDto {
  query!: string;
}

export interface StreamMessage {
  data: string;
  type?: string;
}
