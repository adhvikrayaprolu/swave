import {beforeEach,expect,it,vi} from 'vitest';
import {fireEvent,render,screen,waitFor} from '@testing-library/react';
import {Feed} from './Feed';
import {useFeedStore} from '@/store/feed';
import {api} from '@/api/client';
vi.mock('@/api/client',()=>({api:{catalog:{search:vi.fn()},feed:{getNext:vi.fn()},events:{save:vi.fn()},playlists:{generateDaily:vi.fn()}}}));
vi.mock('@/store/auth',()=>{const user={username:'tester'};return {useAuthStore:()=>({user,isDemoMode:false,logout:vi.fn()})};});
vi.mock('@/components/SwipeCard',()=>({SwipeCard:({track}:{track:{title:string}})=><p>{track.title}</p>}));
const old=[1,2,3].map(id=>({id:String(id),title:'Unrelated seed '+id,artist:'Seed',album:'',artworkUrl:'',previewUrl:null}));
beforeEach(()=>{vi.resetAllMocks();useFeedStore.getState().setExternalQueue(old);});
it('shows catalog matches rather than fetching an unrelated general feed',async()=>{
 vi.mocked(api.catalog.search).mockResolvedValue({imported:1,tracks:[{...old[0],id:'search-result',title:'Matching song'}]});
 render(<Feed/>);fireEvent.change(screen.getByLabelText('Search music'),{target:{value:'Matching'}});fireEvent.click(screen.getByRole('button',{name:'Search'}));
 await waitFor(()=>expect(screen.getByText('Matching song')).not.toBeNull());
 expect(screen.queryByText('Unrelated seed 1')).toBeNull();expect(api.feed.getNext).not.toHaveBeenCalled();
});
it('keeps the visible queue when the search provider fails',async()=>{
 vi.mocked(api.catalog.search).mockRejectedValue(new Error('Catalog unavailable'));
 render(<Feed/>);fireEvent.change(screen.getByLabelText('Search music'),{target:{value:'Matching'}});fireEvent.click(screen.getByRole('button',{name:'Search'}));
 await waitFor(()=>expect((screen.getByRole('button',{name:'Search'}) as HTMLButtonElement).disabled).toBe(false));expect(screen.getByText('Unrelated seed 1')).not.toBeNull();
});
