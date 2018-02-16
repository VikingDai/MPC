import numpy as np
from cost_functions import trajectory_cost_fn
import time
from iLQR import iLQR

class Controller():
	def __init__(self):
		pass

	# Get the appropriate action(s) for this state(s)
	def get_action(self, state, steps):
		pass


class RandomController(Controller):
	def __init__(self, env):
		""" YOUR CODE HERE """
		self.env = env

	def get_action(self, state, steps):
		""" YOUR CODE HERE """
		""" Your code should randomly sample an action uniformly from the action space """
		action = self.env.action_space.sample()
		return action


class MPCcontroller(Controller):
	""" Controller built using the MPC method outlined in https://arxiv.org/abs/1708.02596 """
	def __init__(self,
				 env,
				 dyn_model,
				 horizon=5,
				 cost_fn=None,
				 num_simulated_paths=10,
				 ):
		self.env = env
		self.dyn_model = dyn_model
		self.horizon = horizon
		self.cost_fn = cost_fn
		self.num_simulated_paths = num_simulated_paths

	def get_action(self, state, steps):
		""" YOUR CODE HERE """
		""" Note: be careful to batch your simulations through the model for speed """

		# sample sequeces of action_space
		action_set = np.reshape([self.env.action_space.sample() for i in range(self.num_simulated_paths * self.horizon)], (self.num_simulated_paths, self.horizon, self.env.action_space.shape[0]))

		state = np.repeat(state.reshape([1,-1]), self.num_simulated_paths, axis=0)
		cost = np.zeros([self.num_simulated_paths], dtype = np.float32)

		# predict next next_states
		for i in range(self.horizon):
			next_state = self.dyn_model.predict(state, action_set[:,i,:])

			cost += self.cost_fn(state[:,:], action_set[:,i,:], next_state[:,:])

			state = next_state

		# calculate cost and choose optimal path
		act = np.argmin(cost)
		return action_set[act, 0]

class LQRcontroller(iLQR):

	def __init__(self,
				env,
				delta,
				T,
				dyn_model,
				cost_fn,
				iterations,
				):
		iLQR.__init__(self, env, delta, T, dyn_model, cost_fn)
		self.iterations = iterations

	def get_action(self, state, steps):

		if not steps:
			self.U_hat = np.reshape([np.zeros(self.env.action_space.sample().shape) for i in range(self.T - 1)], (self.T - 1, self.env.action_space.shape[0]))

			self.X_hat = []
			self.X_hat.append(state)
			x = state

			for i in range(self.T - 1):
				next_state = self.dyn_model.predict(x, self.U_hat[i,:])

				self.X_hat.append(next_state[0])
				x = next_state

			self.X_hat = np.asarray(self.X_hat)

		for i in range(self.iterations):
			self.backward(self.X_hat, self.U_hat)

			x = state #X_hat[0]

			U = np.zeros(self.U_hat.shape)
			X = np.zeros(self.X_hat.shape)

			for t in range(self.T - 1):
				u = self.get_action_one_step(x, t, self.X_hat[t], self.U_hat[t])
				#print("control", u)
				X[t] = x
				U[t] = u

				x = self.dyn_model.predict(x, u)[0]

			X[-1] = x
			#print("X_hat for iteration {} is {}".format(i, X_hat))
			#print("U_hat for iteration {} is {}".format(i, self.U_hat))
			self.X_hat = X
			self.U_hat = U

		return self.U_hat[0]
