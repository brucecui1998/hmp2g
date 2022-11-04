import numpy as np
from multiagent.core import World, Agent
from multiagent.scenario import BaseScenario
import cmath, math
try:
    from numba import njit
except:
    from UTIL.tensor_ops import dummy_decorator as njit


def Norm(x):  # 求长度
    return np.linalg.norm(x)


def assert_and_break(cond):
    if cond:
        return
    else:
        print("fail!")


def convert_to_pole2D(vec):
    cn = complex(vec[0], vec[1])
    Range, rad_angle = cmath.polar(cn)
    angle = math.degrees(rad_angle)
    # print(Range, angle)    # (-180,+180]
    return Range, angle


class ScenarioConfig(object):  
    '''
        ScenarioConfig: This config class will be 'injected' with new settings from JSONC.
        (E.g., override configs with ```python main.py --cfg example.jsonc```)
        (As the name indicated, ChainVars will change WITH vars it 'chained_with' during config injection)
        (please see UTIL.config_args to find out how this advanced trick works out.)
    '''
    discrete_action = True
    MaxEpisodeStep = 150

    reach_distance = 0.07

    n_worker = 50
    n_cargo = 4
    # n_destination = 2
    acc = 15

    # ~!
    N_TEAM = 1
    N_AGENT_EACH_TEAM = [n_worker, ]
    AGENT_ID_EACH_TEAM = [list(range(0, n_worker)), ]
    TEAM_NAMES = ['script-team', ]

    num_agent = n_worker
    num_entity = n_cargo * 2

    num_object = n_worker + n_cargo + n_cargo

    uid_dictionary = {
        'agent_uid': range(0, n_worker),
        'entity_uid': range(n_worker, n_worker + n_cargo * 2)
    }
    assert len(uid_dictionary['entity_uid']) == num_entity
    assert len(uid_dictionary['agent_uid']) == num_agent
    obs_vec_length = 5
    obs_vec_dictionary = {
        'pos': (0, 1),
        'vel': (2, 3),
        'mass': (4),
    }
    ObsAsUnity = True
    render = False

class Scenario(BaseScenario):
    def __init__(self, process_id=-1):
        self.n_worker = ScenarioConfig.n_worker
        self.n_agent = sum(ScenarioConfig.N_AGENT_EACH_TEAM)
        self.n_cargo = ScenarioConfig.n_cargo
        self.acc = ScenarioConfig.acc
        self.obs_vec_length = ScenarioConfig.obs_vec_length
        self.reach_distance = ScenarioConfig.reach_distance
        self.work_size = 0.03
        self.process_id = process_id
        self.show_off = False 
        if ScenarioConfig.render and process_id != 0:
            self.show_off = True
        self.cargo_previous = None

    def render(self):
        # if self.mcv is None: return
        # uid = 0
        # for index, worker in enumerate(self.workers):
        #     if worker.dragging < 0:
        #         self.mcv.v2dx('cir|%d|r|%.3f' % (uid, self.work_size), worker.state.p_pos[0], worker.state.p_pos[1])
        #     else:
        #         # m/n
        #         c = worker.dragging
        #         n = len(self.cargo_dragged_by[c])
        #         m = self.cargo_dragged_by[c].index(index)
        #         self.mcv.v2dx('rec|%d|r|%.3f' % (uid, self.work_size),
        #                       worker.state.p_pos[0] + np.cos(m / n * 2 * np.pi) * 0.1,
        #                       worker.state.p_pos[1] + np.sin(m / n * 2 * np.pi) * 0.1)
        #     uid += 1

        # for index, cargo_pos in enumerate(self.cargo):
        #     self.mcv.v2dx('rec|%d|b|%.3f' % (uid, self.cargo_weight[index] / 100), cargo_pos[0], cargo_pos[1])
        #     uid += 1

        # for index, drop_off_pos in enumerate(self.cargo_drop_off):
        #     self.mcv.v2dx('cir|%d|g|%.3f' % (uid, self.cargo_weight[index] / 100), drop_off_pos[0], drop_off_pos[1])
        #     uid += 1

        # self.mcv.xlabel('step: %d,reward: %.2f' % (self.step, self.reward_sample))
        # self.mcv.drawnow()
        return

    def observation(self, agent, world):
        if agent.iden == 0:
            # by now the agents has already moved according to action
            # self.scenario_step(agent, world)  # 第一步更新距离矩阵，更新智能体live的状态
            self.joint_rewards = self.reward_forall(world)  # 第二步更新奖励
            if self.show_off: self.render()  # 第三步更新UI

        self.obs_dimension = self.obs_vec_length * (self.n_worker + 2 * self.n_cargo) + self.obs_vec_length * 1 + 1
        self.obs_pointer = 0  # this is important for function load_obs
        self.obs = np.zeros(shape=(self.obs_dimension,))

        self.load_obs(
            np.concatenate(
                [
                    np.concatenate(
                        (entity.state.p_pos,
                         entity.state.p_vel,
                         [entity.dragging])
                    )
                    for entity in world.agents]
            )
        )
        self.load_obs(
            np.concatenate(
                [
                    np.concatenate(
                        (cargo_pos,
                         [0, 0],
                         [weight])
                    )
                    for cargo_pos, weight in zip(self.cargo, self.cargo_weight)]
            )
        )
        self.load_obs(
            np.concatenate(
                [
                    np.concatenate(
                        (drop_off_pos,
                         [0, 0],
                         [corrisponding_cargo])
                    )
                    for corrisponding_cargo, drop_off_pos in enumerate(self.cargo_drop_off)]
            )
        )
        self.load_obs(
            np.concatenate(
                (agent.state.p_pos,
                 agent.state.p_vel,
                 [0])
            )
        )
        self.load_obs(world.steps)  # do not change, the invader script AI will read
        return self.obs.copy()

    def load_obs(self, fragment):
        L = len(fragment) if isinstance(fragment, np.ndarray) else 1
        # assert self.obs_pointer + L <= self.obs_dimension
        self.obs[self.obs_pointer:self.obs_pointer + L] = fragment
        # print('[%d ~ %d] filled / Total Length %d / total [0 ~ %d]'%(self.obs_pointer, self.obs_pointer + L -1, self.obs_pointer + L, self.obs_dimension-1))
        self.obs_pointer = self.obs_pointer + L


    # def scenario_step(self, agent, world):
    #     pass


    def update_matrix(self):
        return self.update_worker_cargo_matrix(self.n_worker, self.n_cargo, self.worker_pos_arr, self.cargo)
    

    @staticmethod
    @njit
    def update_worker_cargo_matrix(n_worker, n_cargo, workers, cargo):
        worker_cargo_dis = np.zeros((n_worker, n_cargo),np.float64)
        for i_worker, worker_obj in enumerate(workers):
            for j_cargo, cargo_pos in enumerate(cargo):
                worker_cargo_dis[i_worker, j_cargo] = np.linalg.norm(cargo_pos - worker_obj)
        return worker_cargo_dis

    
    def reward_forall(self, world):
        self.step += 1
        # worker 奖励有如下2条
        # <1> CARGO_START_MOVING_REWARD = 0.1
        # <2> CARGO_REACH_DST_REWARD = 1
        worker_reward = np.zeros(self.n_worker)

        CARGO_START_MOVING_REWARD = 0.1
        CARGO_REACH_DST_REWARD = 1
        CARGO_ALL_DONE = 4

        # 获取智能体列表30
        cargo = self.cargo
        cargo_dst = self.cargo_drop_off
        assert cargo is not None
        assert cargo_dst is not None
        self.worker_pos_arr = np.array([w.state.p_pos for w in self.workers])



        shift = self.worker_pos_arr - self.worker_previous_pos \
            if self.worker_previous_pos is not None else np.array([0, 0])

        # 处理cargo运动
        for c in range(self.n_cargo):
            # sum up the agent force(shift) direction, update cargo position
            push_by_n_worker = len(self.cargo_dragged_by[c])
            if push_by_n_worker >= self.cargo_weight[c]:
                holding_agents = [True if w in self.cargo_dragged_by[c] else False for w in range(self.n_worker)]
                shift_ = shift[holding_agents]
                shift_ = shift_.mean(axis=0)
                shift_ = shift_ / (Norm(shift_) + 1e-6) * 0.5 / 10
                if self.cargo_moving[c]:
                    self.cargo[c] += shift_
                if not self.cargo_moving[c]:  # this is the moment that cargo start moving
                    self.cargo_moving[c] = True
                    if self.cargo_hot[c]: worker_reward += CARGO_START_MOVING_REWARD

            # hold old dragging workers at the cargo position
            for w in self.cargo_dragged_by[c]:
                self.worker_pos_arr[w] = self.cargo[c].copy()   # set pos
                
        # if any cargo reach its destination
        cargo_distance = np.linalg.norm((cargo - cargo_dst), axis=-1)
        for c, cargo_reached in enumerate(cargo_distance < self.reach_distance):
            if cargo_reached:
                if self.cargo_hot[c]:
                    worker_reward += CARGO_REACH_DST_REWARD
                    self.cargo_hot[c] = False  # 每个货物只能带来一次奖励
                    if not any(self.cargo_hot):
                        # deliver all done
                        if self.show_off: print('deliver all done')
                        worker_reward += CARGO_ALL_DONE
                        self.cargo_all_delivered = True
                else:
                    pass
                self.cargo[c, :] = self.cargo_init_pos[c, :]
                self.cargo_moving[c] = False
                n = len(self.cargo_dragged_by[c])
                for w in self.cargo_dragged_by[c]:
                    self.workers[w].dragging = -1
                    div_ = np.pi * 2 / n
                    a_ = w * div_
                    self.workers[w].state.p_vel = np.array([np.cos(a_), np.sin(a_)]) * 10
                self.cargo_dragged_by[c].clear()


        self.worker_cargo_dis = self.update_matrix()
        contact_mat = self.worker_cargo_dis < self.reach_distance
        contact_arr = contact_mat.sum(1)
        cargo_contact_arr = contact_mat.sum(0)

        # check if any worker starts a new cargo
        for w in range(self.n_worker):
            if contact_arr[w] > 0:
                c = int(np.argmin(self.worker_cargo_dis[w]))
                if self.workers[w].dragging != c and self.workers[w].dragging != -1:  # 已经在运输其他
                    c = self.workers[w].dragging
                    assert (w in self.cargo_dragged_by[c])
                else:
                    if w not in self.cargo_dragged_by[c]:   # add new drag worker
                        self.cargo_dragged_by[c].append(w)
                        assert self.workers[w].dragging == -1
                        self.workers[w].dragging = c
                        self.worker_pos_arr[w] = self.cargo[c].copy()   # set pos
                        self.workers[w].state.p_vel *= 0                # clear vel
                    else:
                        assert self.workers[w].dragging == c, (self.workers[w].dragging, self.cargo_dragged_by[c])
            else:
                c = self.workers[w].dragging    # the cargo has reached dst
                if c >= 0:
                    assert False
                    # assert w not in self.cargo_dragged_by[c]    # cargo_dragged_by has been clear()
                    self.workers[w].dragging = -1

        self.worker_previous_pos = self.worker_pos_arr.copy()

        self.reward_sample += worker_reward[0]
        self.cargo_previous = self.cargo

        for w in range(self.n_worker):  
            self.workers[w].state.p_pos = self.worker_pos_arr[w]
        return worker_reward.tolist()


    def reset_world(self, world):
        self.step = 0
        self.workers = world.agents

        n_lines = np.sqrt(self.n_worker).astype(np.int)
        n_cols = np.ceil(self.n_worker / n_lines).astype(np.int)

        n_objects = self.n_cargo * 2 + 1
        angle_div = 2 * np.pi / n_objects
        arm = 2

        init_pos_sel = np.zeros(shape=(n_objects, 2))
        for i in range(n_objects):
            angle_ = np.pi - i * angle_div
            init_pos_sel[i] = np.array([np.cos(angle_), np.sin(angle_)]) + np.array([1, 0])
            init_pos_sel[i] *= arm

        y = np.arange(n_objects)
        np.random.shuffle(y)
        init_pos_sel = init_pos_sel.copy()[y]

        worker_init_center = init_pos_sel[0]
        for i in range(n_lines):
            for j in range(n_cols):
                if i * n_cols + j >= self.n_worker: break
                world.agents[int(i * n_cols + j)].state.p_pos = \
                    np.array([0.1 * i - 0.05 * n_lines, 0.1 * j - 0.05 * n_cols]) + worker_init_center

        for agent in self.workers:
            agent.state.p_vel = np.zeros(world.dim_c)
            agent.movable = True
            agent.dragging = -1

        self.cargo = init_pos_sel[1: 1 + self.n_cargo]
        self.cargo_hot = [True for _ in range(self.n_cargo)]
        self.cargo_init_pos = self.cargo.copy()

        self.cargo_weight = np.zeros(self.n_cargo)

        self.cargo_drop_off = init_pos_sel[1 + self.n_cargo:]

        self.cargo_dragged_by = [[] for _ in range(self.n_cargo)]

        average = self.n_worker / self.n_cargo
        # init cargo_weight

        def part_an_int(an_int, n_piece):
            s = np.arange(an_int)
            np.random.shuffle(s)
            s = s[:n_piece-1]
            s = np.concatenate(([0, an_int], s))
            s = np.sort(s)
            w = []
            for i in range(self.n_cargo):
                w.append(s[i + 1] - s[i])
            return w

        # 30% random, 70% average
        base = np.floor(self.n_worker/self.n_cargo*0.7)
        left_space = self.n_worker - base*self.n_cargo
        grow = part_an_int(left_space, self.n_cargo)
        for i in range(self.n_cargo):
            self.cargo_weight[i] = int(grow[i] + base)

        assert self.cargo_weight.sum() == self.n_worker
        # self.cargo_weight

        self.cargo_moving = [False for _ in range(self.n_cargo)]
        self.worker_previous_pos = None
        world.steps = 0
        self.reward_sample = 0
        self.cargo_all_delivered = False
        if self.show_off:
            print('reset world')

    def reward(self, agent, world):
        assert self.joint_rewards is not None
        reward = self.joint_rewards[agent.iden]
        if agent.iden == self.n_agent:
            self.joint_rewards = None
        return reward

    def done(self, agent, world):
        condition1 = world.steps >= world.MaxEpisodeStep
        condition_success = self.cargo_all_delivered
        return condition1 or condition_success


    def check_obs(self):
        assert self.obs_pointer == self.obs_dimension

    def info(self, agent, world):
        return {'world_steps': world.steps}

    def make_world(self):
        world = World()  # set any world properties first
        world.dim_c = 2
        n_agent = self.n_worker
        world.agents = [Agent(iden=i) for i in range(n_agent)]
        for i, agent in enumerate(world.agents):
            agent.name = 'agent %d' % i
            agent.collide = False  # no collide
            agent.silent = True
            agent.id_in_team = i
            agent.size = 1
            agent.accel = self.acc
            agent.max_speed = 10 * 0.15
            agent.live = True
            agent.movable = True
            agent.initial_mass = 15
        self.workers = world.agents
        self.cargo = None
        self.cargo_drop_off = None
        self.reset_world(world)
        world.MaxEpisodeStep = ScenarioConfig.MaxEpisodeStep
        return world

    @staticmethod
    def rand(low, high):
        return np.random.rand() * (high - low) + low
