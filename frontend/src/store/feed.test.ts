import {beforeEach,expect,it,vi} from 'vitest';
import {useFeedStore} from './feed';
import {api} from '@/api/client';
vi.mock('@/api/client',()=>({api:{feed:{getNext:vi.fn()}}}));
const song={id:'1',title:'Song',artist:'Artist',album:'',artworkUrl:'',previewUrl:null};
beforeEach(()=>{vi.resetAllMocks();useFeedStore.getState().reset();});
it('keeps a track when saving fails so the user can retry',async()=>{
 useFeedStore.getState().setExternalQueue([song]);
 await expect(useFeedStore.getState().consumeTop(()=>Promise.reject(new Error('Offline')))).rejects.toThrow('Offline');
 expect(useFeedStore.getState().queue).toEqual([song]);
});
it('removes only a successfully saved track and handles refill failure',async()=>{
 useFeedStore.getState().setExternalQueue([song]);
 vi.mocked(api.feed.getNext).mockRejectedValue(new Error('Network unavailable'));
 await useFeedStore.getState().consumeTop(()=>Promise.resolve());
 expect(useFeedStore.getState().queue).toEqual([]);
 expect(useFeedStore.getState().error).toBe('Network unavailable');
});
it('clears a failed load on retry',async()=>{
 vi.mocked(api.feed.getNext).mockRejectedValueOnce(new Error('Offline')).mockResolvedValueOnce({batchId:'batch',tracks:[song]});
 await useFeedStore.getState().fetchIfLow();await useFeedStore.getState().fetchIfLow();
 expect(useFeedStore.getState().error).toBeNull();expect(useFeedStore.getState().queue).toEqual([song]);
});
