import axios from 'axios';
import { sendMessage, uploadFile, getConversations, deleteConversation } from './api';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('API Service', () => {
  beforeEach(() => {
    mockedAxios.create.mockReturnValue(mockedAxios);
  });

  test('sendMessage calls correct endpoint', async () => {
    const mockResponse = { message: 'Response', conversation_id: '123' };
    mockedAxios.post.mockResolvedValue({ data: mockResponse });

    const request = { message: 'Test', conversation_id: null, file_context: null };
    const result = await sendMessage(request);

    expect(mockedAxios.post).toHaveBeenCalledWith('/api/chat', request);
    expect(result).toEqual(mockResponse);
  });

  test('getConversations fetches conversations', async () => {
    const mockConversations = [
      {
        conversation_id: '1',
        title: 'Test',
        created_at: '2024-01-01',
        updated_at: '2024-01-01',
        message_count: 2,
      },
    ];
    mockedAxios.get.mockResolvedValue({ data: mockConversations });

    const result = await getConversations();

    expect(mockedAxios.get).toHaveBeenCalledWith('/api/conversations');
    expect(result).toEqual(mockConversations);
  });

  test('deleteConversation calls delete endpoint', async () => {
    mockedAxios.delete.mockResolvedValue({ data: {} });

    await deleteConversation('123');

    expect(mockedAxios.delete).toHaveBeenCalledWith('/api/conversations/123');
  });
});
