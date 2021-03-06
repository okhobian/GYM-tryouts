import os
import gym
import cv2
import numpy as np

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Flatten, Convolution2D
from tensorflow.keras.optimizers import Adam, RMSprop
from tensorflow.keras.callbacks import CSVLogger

from rl.agents import DQNAgent
from rl.memory import SequentialMemory
from rl.policy import LinearAnnealedPolicy, EpsGreedyQPolicy
from rl.callbacks import ModelIntervalCheckpoint, FileLogger
from rl.core import Processor

# to enable GPU for TensorFlow
ENABLE_GPU = True

# Constant parameters
ENV_NAME = 'Breakout-v0'    
NUM_STEPS = 500000          # number of actions to perform

# File paths
DIR_PATH = os.path.dirname(os.path.realpath(__file__))
INSTANCE_PATH = os.path.join(DIR_PATH, 'logs', ENV_NAME, '{}_steps'.format(NUM_STEPS))
CHECKPOINTS_PATH = os.path.join(INSTANCE_PATH, 'checkpoints')

class CustomerProcessor(Processor):
    """Overwrites the Processor class from rl.core
       - apply custome process_step
       - apply custome state obvervation
       - apply custome reward
    """
    def process_step(self, observation, reward, done, info):
        observation = self.process_observation(observation)
        reward = self.process_reward(reward)
        info = self.process_info(info)
        return observation, reward, done, info
    
    def process_observation(self, observation):
        # convert RGB state img to Gray scale
        img = cv2.cvtColor(observation, cv2.COLOR_BGR2GRAY)
        img = img.reshape(img.shape[0], img.shape[1], 1)        
        return img
    
    def process_reward(self, reward):
        # use default reward
        return reward

def build_callbacks(env_name):
    """This function is used to build the callbacks for DQNAgent training. Including weight/log saving

        # Arguments
            env_name (string): the current environment name

        # Returns
            callbacks (list): a list of callback instances
    """
    
    checkpoint_weights_filename = CHECKPOINTS_PATH + '\\dqn_' + env_name + '_weights_{step}.h5f'
    log_filename = INSTANCE_PATH + '\\dqn_{}_log.json'.format(env_name)
    callbacks = [ModelIntervalCheckpoint(checkpoint_weights_filename, interval=50000)]
    callbacks += [FileLogger(log_filename, interval=500)]
    return callbacks

def build_model(height, width, actions):
    """This function is used to build the nerual network model for DQNAgent

        # Arguments
            height (int): state image height
            width (int): state image width
            actions (list): the avaiable actions:
                [NOOP, FIRE, RIGHT, LEFT]

        # Returns
            model: multi-layer convolution network
    """
    
    shape = (3, height, width, 1)
    # shape = (3, 210, 160, 1)
    model = Sequential()
    model.add(Convolution2D(32, (8,8), strides=(4,4), activation='relu', input_shape=shape))
    model.add(Convolution2D(64, (4,4), strides=(2,2), activation='relu'))
    model.add(Convolution2D(64, (3,3), activation='relu'))
    model.add(Flatten())
    model.add(Dense(512, activation='relu'))
    model.add(Dense(256, activation='relu'))
    model.add(Dense(actions, activation='linear'))
    return model

def build_agent(model, actions):
    """This function is used to build the DQNAgent

        # Arguments
            model: multi-layer convolution network
            actions (list): the avaiable actions:
                [NOOP, FIRE, RIGHT, LEFT]

        # Returns
            dqn: DQNAgent()
    """
    
    policy = LinearAnnealedPolicy(EpsGreedyQPolicy(), 
                                  attr='eps', 
                                  value_max=1., 
                                  value_min=.1, 
                                  value_test=.2, 
                                  nb_steps=NUM_STEPS
    )
    memory = SequentialMemory(limit=1000, window_length=3)
    dqn = DQNAgent(model=model, 
                   processor=CustomerProcessor(), 
                   memory=memory, 
                   policy=policy,
                   enable_dueling_network=True, 
                   dueling_type='avg', 
                   nb_actions=actions, 
                   nb_steps_warmup=1000
    )
    return dqn


if __name__ == "__main__":

    if not ENABLE_GPU:
        os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
        
    if not os.path.exists(INSTANCE_PATH):
        os.makedirs(INSTANCE_PATH)
        
    if not os.path.exists(CHECKPOINTS_PATH):
        os.makedirs(CHECKPOINTS_PATH)

    # initialize environment
    env = gym.make(ENV_NAME)
    height, width, channels = env.observation_space.shape
    actions = env.action_space.n
    action = env.unwrapped.get_action_meanings()
    print(action)
    print(height, width, channels)

    # create neural network
    model = build_model(height, width, actions)
    model.summary()

    # create DQNAgent
    dqn = build_agent(model, actions)
    # optimizer = RMSprop(lr=0.00025, rho=0.95, epsilon=0.01)
    optimizer = Adam(lr=1e-4)
    dqn.compile(optimizer, metrics=['mse'])
    
    # fit agent
    callbacks = build_callbacks(ENV_NAME)
    dqn.fit(env, 
            nb_steps=NUM_STEPS, 
            visualize=False, 
            callbacks=callbacks, 
            verbose=2
    )
    dqn.save_weights(INSTANCE_PATH + '\\finished_weights.h5f')

    # test agent
    scores = dqn.test(env, nb_episodes=10, visualize=True)
    print(np.mean(scores.history['episode_reward']))